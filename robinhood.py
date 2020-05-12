import datetime
import math
import os
import sys
from datetime import datetime

from pyrh import Robinhood
from twilio.rest import Client
from lib.emailer import Emailer
from lib.helper import stock_id

u = os.getenv('user')
p = os.getenv('pass')
q = os.getenv('qr')

if not u or not p or not q:
    print("Check your local environment variables. It should be set as:\n\n"
          "'user=<login_email>'\n'pass=<password>'\n'qr=<qr_code>'")
    sys.exit()

rh = Robinhood()
rh.login(username=u, password=p, qr_code=q)

if rh.get_quote('EXPE')['trading_halted'] is False:
    print('Gathering your investment details...')
else:
    print("I'm not supposed to run during after market hours in order to save $$. Please check for yourself.")
    sys.exit()


def account_user_id():
    ac = rh.get_account()
    user = ac['account_number']
    return user


def portfolio_value():
    port = rh.portfolios()
    current_val = port['equity']
    current_value = round(float(current_val), 2)
    return current_value


def watcher():
    acc_id = account_user_id()
    raw_result = (rh.positions())
    result = raw_result['results']
    share_code = dict(stock_id())
    shares_total = []
    port_msg = f'Your portfolio ({acc_id}):\n'
    loss_output = 'Loss:'
    profit_output = 'Profit:'
    for data in result:
        share_id = str(data['instrument'].split('/')[-2])
        buy = round(float(data['average_buy_price']), 2)
        shares_count = data['quantity'].split('.')[0]
        for key, value in share_code.items():
            if str(value) == share_id:
                share_name = key.split("|")[0]
                share_full_name = key.split("|")[1]
                total = round(int(shares_count) * float(buy), 2)
                shares_total.append(total)  # not used in this function
                current = round(float(rh.get_quote(share_name)['last_trade_price']), 2)
                current_total = round(int(shares_count) * current, 2)
                difference = round(float(current_total - total), 2)
                if difference < 0:
                    loss_output += (f'\n{shares_count} shares of {share_name} at ${buy} Currently: ${current}\n'
                                    f'Total bought: ${total} Current Total: ${current_total}'
                                    f'\nLOST ${-difference} on {share_full_name}\n')
                else:
                    profit_output += (f'\n{shares_count} shares of {share_name} at ${buy} Currently: ${current}\n'
                                      f'Total bought: ${total} Current Total: ${current_total}'
                                      f'\nGained ${difference} on {share_full_name}\n')

    net_worth = portfolio_value()
    output_ = f'\nCurrent value of your total investment is: ${net_worth}'
    total_buy = round(math.fsum(shares_total), 2)
    output_ += f'\nValue of your total investment while purchase is: ${total_buy}'
    total_diff = round(float(net_worth - total_buy), 2)
    if total_diff < 0:
        output_ += f'\nOverall Loss: ${total_diff}'
    else:
        output_ += f'\nOverall Profit: ${total_diff}'
    return port_msg, profit_output, loss_output, output_


port_head, profit, loss, overall_result = watcher()


def send_email():
    sender_env = os.getenv('SENDER')
    recipient_env = os.getenv('RECIPIENT')
    logs = 'https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logStream:group=/aws/lambda' \
           '/stock_hawk '
    git = 'https://github.com/vignesh1793/robinhood_tracker'
    footer_text = "\n----------------------------------------------------------------" \
                  "----------------------------------------\n" \
                  "A report on the list shares you have purchased.\n" \
                  "The data is being collected using http://api.robinhood.com/," \
                  f"\nFor more information check README.md in {git}"
    sender = f'Robinhood Monitor <{sender_env}>'
    recipient = [f'{recipient_env}']
    title = 'Robinhood Alert'
    text = f'{overall_result}\n\n{port_head}\n{profit}\n\n{loss}\n\nNavigate to check logs: {logs}\n\n{footer_text}'
    email = Emailer(sender, recipient, title, text)
    return email


# two arguments for the below functions as lambda passes event, context by default
def send_whatsapp(data, context):
    if send_email():
        now = datetime.now()
        dt_string = now.strftime("%A, %B %d, %Y %I:%M %p")
        sid = os.getenv('SID')
        token = os.getenv('TOKEN')
        sender = f"whatsapp:{os.getenv('SEND')}"
        receiver = f"whatsapp:{os.getenv('RECEIVE')}"
        client = Client(sid, token)
        from_number = sender
        to_number = receiver
        client.messages.create(body=f'{dt_string}\nRobinhood Notification\n{overall_result}\n\nCheck your email for '
                                    f'summary',
                               from_=from_number,
                               to=to_number)
    else:
        return None


if __name__ == '__main__':
    send_whatsapp("data", "context")
