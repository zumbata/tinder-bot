import os, time

def main():
    startAcc = int(input(" > Enter first account id: "))
    finishAcc = int(input(" > Enter last account id: "))
    for i in range(startAcc, finishAcc+1):
        print(" > Loading a NordVPN server...")
        os.system(r'cd "C:\Program Files (x86)\NordVPN" && nordvpn -c -g "United States"')
        time.sleep(30)
        print(" > NordVPN server is online.")
        print(f" > Starting bot with account #{i}.")
        os.system(f'cd "{os.getcwd()}" && python bot.py {i}')

main()