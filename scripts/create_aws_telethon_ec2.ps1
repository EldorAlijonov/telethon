param(
    [string]$Region = "eu-north-1",
    [string]$Name = "telethon-bot",
    [string]$InstanceType = "t3.small",
    [int]$VolumeSizeGb = 20,
    [string]$KeyPath = "C:\Users\EldorAlijonov\Downloads\Vidogram\key.pem",
    [string]$KeyName = "vidogram-key",
    [string]$SecurityGroupName = "telethon-bot-ssh"
)

$ErrorActionPreference = "Stop"

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name topilmadi. Avval o'rnating yoki PATH ni yangilang."
    }
}

Require-Command aws
Require-Command ssh-keygen

$identity = aws sts get-caller-identity --output json | ConvertFrom-Json
Write-Host "AWS account ulandi: $($identity.Account)"

$myIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
$cidr = "$myIp/32"
Write-Host "SSH faqat shu IP uchun ochiladi: $cidr"

$amiId = aws ssm get-parameter `
    --region $Region `
    --name "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id" `
    --query "Parameter.Value" `
    --output text
Write-Host "Ubuntu AMI: $amiId"

$vpcId = aws ec2 describe-vpcs `
    --region $Region `
    --filters "Name=isDefault,Values=true" `
    --query "Vpcs[0].VpcId" `
    --output text
if (-not $vpcId -or $vpcId -eq "None") {
    throw "Default VPC topilmadi. AWS Console'da VPC/Subnet tanlash kerak."
}

$sgId = aws ec2 describe-security-groups `
    --region $Region `
    --filters "Name=group-name,Values=$SecurityGroupName" "Name=vpc-id,Values=$vpcId" `
    --query "SecurityGroups[0].GroupId" `
    --output text
if (-not $sgId -or $sgId -eq "None") {
    $sgId = aws ec2 create-security-group `
        --region $Region `
        --group-name $SecurityGroupName `
        --description "SSH access for telethon bot server" `
        --vpc-id $vpcId `
        --query "GroupId" `
        --output text
    Write-Host "Security group yaratildi: $sgId"
}

try {
    aws ec2 authorize-security-group-ingress `
        --region $Region `
        --group-id $sgId `
        --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=$cidr,Description='SSH from current IP'}]" | Out-Null
    Write-Host "SSH rule qo'shildi."
} catch {
    Write-Host "SSH rule allaqachon mavjud bo'lishi mumkin."
}

$existingKey = aws ec2 describe-key-pairs `
    --region $Region `
    --key-names $KeyName `
    --query "KeyPairs[0].KeyName" `
    --output text 2>$null
if (-not $existingKey -or $existingKey -eq "None") {
    $publicKey = ssh-keygen -y -f $KeyPath
    $publicKeyFile = Join-Path $env:TEMP "$KeyName.pub"
    Set-Content -Path $publicKeyFile -Value $publicKey -NoNewline
    aws ec2 import-key-pair `
        --region $Region `
        --key-name $KeyName `
        --public-key-material "fileb://$publicKeyFile" | Out-Null
    Remove-Item $publicKeyFile -Force
    Write-Host "Key pair import qilindi: $KeyName"
}

$instanceId = aws ec2 run-instances `
    --region $Region `
    --image-id $amiId `
    --instance-type $InstanceType `
    --key-name $KeyName `
    --security-group-ids $sgId `
    --block-device-mappings "[{`"DeviceName`":`"/dev/sda1`",`"Ebs`":{`"VolumeSize`":$VolumeSizeGb,`"VolumeType`":`"gp3`",`"DeleteOnTermination`":true}}]" `
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$Name},{Key=Project,Value=telethon}]" "ResourceType=volume,Tags=[{Key=Name,Value=$Name-root},{Key=Project,Value=telethon}]" `
    --query "Instances[0].InstanceId" `
    --output text

Write-Host "Instance yaratildi: $instanceId"
aws ec2 wait instance-running --region $Region --instance-ids $instanceId

$publicIp = aws ec2 describe-instances `
    --region $Region `
    --instance-ids $instanceId `
    --query "Reservations[0].Instances[0].PublicIpAddress" `
    --output text

Write-Host "Tayyor."
Write-Host "Instance ID: $instanceId"
Write-Host "Public IP: $publicIp"
Write-Host "SSH: ssh -i `"$KeyPath`" ubuntu@$publicIp"
