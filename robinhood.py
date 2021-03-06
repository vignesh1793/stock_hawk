"""/**
 * Author:  Vignesh Sivanandha Rao
 * Created:   05.08.2020
 *
 **/"""
import json
import math
import os
import time
from datetime import datetime, timedelta, date

import requests
from pandas import read_html as reader
from pyrh import Robinhood
from twilio.rest import Client

from lib.emailer import Emailer


def market_status():
    url = 'https://www.nasdaqtrader.com/trader.aspx?id=Calendar'
    holidays_list = list(reader(url)[0][0])
    today = date.today().strftime("%B %d, %Y")
    if today in holidays_list:
        print(f'{today}: The markets are closed today.')
    else:
        return True


def watcher():
    global graph_msg
    raw_result = (rh.positions())
    result = raw_result['results']
    shares_total = []
    port_msg = f"Your portfolio ({rh.get_account()['account_number']}):\n"
    loss_output = 'Loss:'
    profit_output = 'Profit:'
    loss_total = []
    profit_total = []
    graph_msg = None  # initiates a variable graph_msg as None for looped condition below
    n = 0
    n_ = 0
    for data in result:
        share_id = str(data['instrument'].split('/')[-2])
        buy = round(float(data['average_buy_price']), 2)
        shares_count = int(data['quantity'].split('.')[0])
        if shares_count != 0:
            n = n + 1
            n_ = n_ + shares_count
        else:
            continue
        raw_details = rh.get_quote(share_id)
        share_name = raw_details['symbol']
        call = raw_details['instrument']
        r = requests.get(call)
        response = r.text
        json_load = json.loads(response)
        share_full_name = json_load['simple_name']
        total = round(shares_count * float(buy), 2)
        shares_total.append(total)
        current = round(float(raw_details['last_trade_price']), 2)
        current_total = round(shares_count * current, 2)
        difference = round(float(current_total - total), 2)
        if difference < 0:
            loss_output += (
                f'\n{share_full_name}:\n{shares_count} shares of {share_name} at ${buy} Currently: ${current}\n'
                f'Total bought: ${total} Current Total: ${current_total}'
                f'\nLOST ${-difference}\n')
            loss_total.append(-difference)
        else:
            profit_output += (
                f'\n{share_full_name}:\n{shares_count} shares of {share_name} at ${buy} Currently: ${current}\n'
                f'Total bought: ${total} Current Total: ${current_total}'
                f'\nGained ${difference}\n')
            profit_total.append(difference)
        if os.getenv('graph_min') and os.getenv('graph_max'):
            graph_min = float(os.getenv('graph_min'))
            graph_max = float(os.getenv('graph_max'))
            if difference > graph_max or difference < -graph_min:
                import matplotlib.pyplot as plt
                time_now = datetime.now()
                metrics = time_now - timedelta(days=7)
                start = metrics.strftime('%m-%d %H:%M')
                end = time_now.strftime('%m-%d %H:%M')
                numbers = []
                historic_data = (rh.get_historical_quotes(share_name, '10minute', 'week'))
                historic_results = historic_data['results']
                historical_values = historic_results[0]['historicals']
                for close_price in historical_values:
                    numbers.append(round(float(close_price['close_price']), 2))
                fig, ax = plt.subplots()
                if difference > graph_max:
                    plt.title(f"Stock Price Trend for {share_full_name}\nProfit: ${difference}")
                elif difference < graph_min:
                    plt.title(f"Stock Price Trend for {share_full_name}\nLOSS: ${-difference}")
                plt.xlabel(f"1 Week trend with 10 minutes interval from {start} to {end}")
                plt.ylabel('Price in USD')
                ax.plot(numbers, linewidth=1.5)
                if not os.path.isdir('img'):
                    os.mkdir('img')
                fig.savefig(f"img/{share_full_name}.png", format="png")
                plt.close()  # close plt to avoid memory exception when more than 20 graphs are generated
                # stores graph_msg only if a graph is generated else graph_msg remains None
                if not graph_msg:  # used if not to avoid storing the message repeatedly
                    graph_msg = f"Attached are the graphs for stocks which exceeded a profit of " \
                                f"${os.getenv('graph_max')} or deceeded a loss of ${os.getenv('graph_min')}"
        elif not graph_msg:  # used elif not to avoid storing the message repeatedly
            graph_msg = "Add the env variables for <graph_min> and <graph_max> to include a graph of previous " \
                        "week's trend."

    lost = round(math.fsum(loss_total), 2)
    gained = round(math.fsum(profit_total), 2)
    port_msg += f'The below values will differ from overall profit/loss if shares were purchased ' \
                f'with different price values.\nTotal Profit: ${gained}\nTotal Loss: ${lost}\n'
    net_worth = round(float(rh.equity()), 2)
    output = f'Total number of stocks purchased: {n}\n'
    output += f'Total number of shares owned: {n_}\n\n'
    output += f'Current value of your total investment is: ${net_worth}\n'
    total_buy = round(math.fsum(shares_total), 2)
    output += f'Value of your total investment while purchase is: ${total_buy}\n'
    total_diff = round(float(net_worth - total_buy), 2)
    if total_diff < 0:
        output += f'Overall Loss: ${total_diff}'
    else:
        output += f'Overall Profit: ${total_diff}'
    yesterday_close = round(float(rh.equity_previous_close()), 2)
    two_day_diff = round(float(net_worth - yesterday_close), 2)
    output += f"\n\nYesterday's closing value: ${yesterday_close}"
    if two_day_diff < 0:
        output += f"\nCurrent Dip: ${two_day_diff}"
    else:
        output += f"\nCurrent Spike: ${two_day_diff}"
    if not graph_msg:  # if graph_msg was not set above
        graph_msg = f"You have not lost more than ${os.getenv('graph_min')} or gained more than " \
                    f"${os.getenv('graph_max')} to generate a graph."

    return port_msg, profit_output, loss_output, output, graph_msg


def send_email(attachment):
    print("Sending email...")
    sender_env = os.getenv('SENDER')
    recipient_env = os.getenv('RECIPIENT')
    git = 'https://github.com/thevickypedia/robinhood_monitor'
    footer_text = "\n----------------------------------------------------------------" \
                  "----------------------------------------\n" \
                  "A report on the list shares you have purchased.\n" \
                  "The data is being collected using http://api.robinhood.com/," \
                  f"\nFor more information check README.md in {git}"
    sender = f'Robinhood Monitor <{sender_env}>'
    recipient = [f'{recipient_env}']
    title = f'Investment Summary as of {dt_string}'
    text = f'{overall_result}\n\n{port_head}\n{profit}\n{loss}\n\n{graph_msg}\n\n{footer_text}'
    Emailer(sender, recipient, title, text, attachment)
    if 'Attached' in graph_msg:  # only tries to delete if graphs have been generated
        import shutil
        shutil.rmtree('img')


def send_whatsapp():
    print('Sending whats app notification...')
    sid = os.getenv('SID')
    token = os.getenv('TOKEN')
    sender = f"whatsapp:{os.getenv('SEND')}"
    receiver = f"whatsapp:{os.getenv('RECEIVE')}"
    client = Client(sid, token)
    from_number = sender
    to_number = receiver
    client.messages.create(body=f'{dt_string}\nRobinhood Report\n{overall_result}\n\nCheck your email for '
                                f'summary',
                           from_=from_number,
                           to=to_number)


if __name__ == '__main__':
    if market_status():
        start_time = time.time()
        u = os.getenv('user')
        p = os.getenv('pass')
        q = os.getenv('qr')
        if not u or not p or not q:
            print("\nCheck your local environment variables. It should be set as:\n"
                  "'user=<login_email>'\n'pass=<password>'\n'qr=<qr_code>'")
            exit(1)
        rh = Robinhood()
        rh.login(username=u, password=p, qr_code=q)
        now = datetime.now()
        dt_string = now.strftime("%A, %B %d, %Y %I:%M %p")
        print(f'\n{dt_string}')
        print('Gathering your investment details...')
        port_head, profit, loss, overall_result, graph_msg = watcher()
        send_email(attachment=True)
        send_whatsapp()
        print(f"Process Completed in {round(float(time.time() - start_time), 2)} seconds")
