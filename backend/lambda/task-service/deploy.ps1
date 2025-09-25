# deploy.ps1
Compress-Archive -Path lambda_function.py -DestinationPath function.zip -Force
aws lambda update-function-code --function-name TaskServiceLambda --zip-file fileb://function.zip
Remove-Item function.zip
Write-Output "Deploy concluído!"