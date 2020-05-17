## Note: 
This sub folder contains scripts that run on lambda connecting to SSM. Using SSM connector, I got rid of local environment variables which improves secured storage.

## Setup

##### Prerequisites:
* Running a script on AWS without a deployment tool like jenkins, requires all the libraries/packages to be locally maintained. 
* Use the [AWS.zip](https://github.com/vignesh1793/robinhood_tracker/tree/master/AWS_lambda_using_ssm/AWS.zip) file and use the same format if libraries had to be changed.

##### Quick tip:
* pip install any package and cd to the location where it has installed.
* cp -r "package name" in to copy the package to a different folder.
* wrap everything together as a .zip file and upload it to AWS.
* root file should be directly accessible within the .zip, so don't include any unnecessary additional sub-folders.

##### 1. Below are the parameters that has to be on your AWS SSM.

* Name = user; Value = Robinhood login email address
* Name = pass; Value = Robinhood login password
* Name = qr; Value = Robinhood MFA QR code (Check for steps in original [README.md](https://github.com/vignesh1793/robinhood_tracker/blob/master/README.md))
* Name = ACCESS_KEY; Value = AWS login access key
* Name = SECRET_KEY; Value = AWS secret key
* Name = SENDER; Value = sender email address (verified via AWS SES)
* Name = RECIPIENT; Value = receiver email address (verified via AWS SES)
<br/><br/>Optional (If you'd like to setup whats app notifications else skip these, app will still run):
* Name = SID; Value = S-ID from twilio
* Name = TOKEN; Value = Token from twilio
* Name = SEND; Value = sender whats app number (fromat - +1xxxxxxxxxx)
* Name = RECEIVE; Value = receiver whats app number (fromat - +1xxxxxxxxxx)<br><br>

##### 2. Setup lambda function and attach an IAM policy

* Create a lambda function with the handler as robinhood.send_whatsapp (this will invoke the send_whats app function inside the robinhood.py file)
* Create an IAM policy with read access to GetParameter and attached to the executing lambda function.
* Once that is done, make sure to check your lambda function's permission to SSM.
* Policy update time: ~5-10 minutes.

##### 3. If you like to setup a cron schedule:
* Add trigger to your lambda function (Trigger name: CloudWatch Events/EventBridge)
* Refer [aws docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html) for scheduling format.