# Update Sourece Code Bot.py
# python Update Boy is not git pull
# u.py

import os


def Delete_File() :
    try :
        #check file bot
        if os.path.exists('bot.py') :
            print("Check[YES]")
            #python rm [file_Name]
            #Linux del [file_Name]
            os.system('rm bot.py')
            if os.path.exists('bot.py') :
                print("Delete[YES]")
        else :
            print("NO")
    except Exception as e :
        print(f"Error(ข้อผิดพลาดน่า) : {e}")

def Update() :
    try :
        print("Update[YES]")
        print("--กำลังอัปเดต--")
        os.system('git clone https://github.com/HamzterDev/Calender.git')
        if os.path.exists('bot.py') :
            print("ติดตั้งเสร็จสิ้น")
    except Exception as e :
        print(f"Error(ข้อผิดพลาดน่า) : {e}")
Delete_File()
Update()
