from tkinter import *
import tkinter.messagebox
from tkinter.font import Font
import tkinter.ttk as ttk
import pandas as pd
from threading import Thread

import socket

import datetime as dt
import time
import os

import board
import adafruit_dht
from PMS7003 import PMS7003
import serial

import warnings

from flask import Flask, render_template

app = Flask(__name__)

warnings.filterwarnings('ignore')

#데이터 업데이트 주기(초)
#먼지센서 값을 읽는데 1초가 걸리므로 원하는 업데이트 주기 값에서 1을 빼줌
update_time = 29
alert_set = 0 #정상범위 외 수치에 대한 경고시의 기준. 0이면 기본, 1이면 커스텀

#각 수치의 좋음, 나쁨 등의 기준
dust_good = 30; dust_normal = 80; dust_bad = 150
mdust_good = 15; mdust_normal = 35; mdust_bad = 75
tmp_cold = 10; tmp_normal = 25; tmp_warm = 30

#온습도 센서 객체
mydht = adafruit_dht.DHT11(board.D2)

#먼지센서 시리얼 통신 연결
dust = PMS7003()
Speed = 9600
UART = '/dev/ttyAMA2'
SERIAL_PORT = UART
ser = serial.Serial(SERIAL_PORT, Speed, timeout= 1)


#데이터 기록 파일
file = 'airdata.csv'
try:
    airdata = pd.read_csv(file)
except:
    airdata = pd.DataFrame(columns= ['date', 'time', 'temp', 'hum', 'dust', 'mdust'])

data = 'airdata.csv'
df = airdata.copy()

#경고등 기준이 저장되어있는 파일
val_set_file = 'val_set.csv'
try:
    val_set = pd.read_csv(val_set_file)
except:
    val_set = pd.DataFrame(columns= ['name', 'temp', 'hum', 'dust', 'mdust'])
    name_basic = 'basic'
    temp_basic = '19-26'
    hum_basic = '40-60'
    dust_basic = dust_normal
    mdust_basic = mdust_normal
    
    val_basic = [name_basic, temp_basic, hum_basic, dust_basic, mdust_basic]
    val_set.loc[val_set.shape[0]] = val_basic
    
    name_custom = 'custom'
    temp_custom = '0-0'
    hum_custom = '0-0'
    dust_custom = 0
    mdust_custom = 0
    
    val_custom = [name_custom, temp_custom, hum_custom, dust_custom, mdust_custom]
    val_set.loc[val_set.shape[0]] = val_custom
    
    val_set.to_csv(val_set_file, index= False)

#웹 페이지 주소를 알기 위해 IP를 얻어오는 함수
def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip    
        
    
#온도에 따른 글자색
def getTmpColor(tmp):
            if tmp < tmp_cold:
                return 'blue'
            elif tmp < tmp_normal:
                return 'black'
            elif tmp < tmp_warm:
                return 'orange'
            else:
                return 'red'

#미세먼지 수치에 따라 화면에 표시할 상태와 글자색
def getDustInfo(dust):
    if dust <= dust_good:
        return ['좋음', 'blue']
    elif dust <= dust_normal:
        return ['보통', 'green']
    elif dust <= dust_bad:
        return ['나쁨', 'orange']
    else:
        return ['매우나쁨', 'red']

#초미세먼지 수치에 따라 화면에 표시할 상태 및 글자색
def getMdustInfo(mdust):
    if mdust <= mdust_good:
        return ['좋음', 'blue']
    elif mdust <= mdust_normal:
        return ['보통', 'green']
    elif mdust <= mdust_bad:
        return ['나쁨', 'orange']
    else:
        return ['매우나쁨', 'red']
    
#설정된 기준 범위에 따라 각 수치가 기준치인지 또는 낮은지, 높은지를 판별
def getAlert(temp, hum, dust, mdust):
    global alert_set, val_set
    
    temp_val = val_set.loc[alert_set, 'temp']
    temp_val = temp_val.split('-')
    temp_low = int(temp_val[0])
    temp_high = int(temp_val[1])
    
    hum_val = val_set.loc[alert_set, 'hum']
    hum_val = hum_val.split('-')
    hum_low = int(hum_val[0])
    hum_high = int(hum_val[1])
    
    dust_val = val_set.loc[alert_set, 'dust']
    mdust_val = val_set.loc[alert_set, 'mdust']
    
    alert_state = [] #-1: low, 0:normal, 1:high
    
    if temp < temp_low:
        alert_state.append(-1)
    elif temp > temp_high:
        alert_state.append(1)
    else:
        alert_state.append(0)
    
    if hum < hum_low:
        alert_state.append(-1)
    elif hum > hum_high:
        alert_state.append(1)
    else:
        alert_state.append(0)
    
    if dust <= dust_val:
        alert_state.append(0)
    else:
        alert_state.append(1)
    
    if mdust <= mdust_val:
        alert_state.append(0)
    else:
        alert_state.append(1)
    
    return alert_state
    
#frmae을 전환
def openFrame(frame):
    frame.tkraise()

#웹페이지 주소 안내 메시지박스
def msgbox_internet():
    link = 'http://' + getIP() + ':5000/get_data'
    tkinter.messagebox.showinfo('정보','아래 주소로 접속하여 모니터링 가능\n' + link)

#정상 범위 설정 창에서 Entry객체의 값을 수정하기 위해 'normal'상태로 전환
def setentrynormal():
    text_temp_low.configure(state= 'normal')
    text_temp_high.configure(state= 'normal')
    text_hum_low.configure(state= 'normal')
    text_hum_high.configure(state= 'normal')
    text_dust.configure(state= 'normal')
    text_mdust.configure(state= 'normal')

#정상 범위 설정 창에서 Entry객체의 값을 수정 한 후에 읽기 전용 상태로 전환
def setentryreadonly():
    text_temp_low.configure(state= 'readonly')
    text_temp_high.configure(state= 'readonly')
    text_hum_low.configure(state= 'readonly')
    text_hum_high.configure(state= 'readonly')
    text_dust.configure(state= 'readonly')
    text_mdust.configure(state= 'readonly')

#정상 범위 설정 창에서 Entry객체의 값을 gap만큼 증가시킴.
#단, maxval 을 초과하지 않음.
def entryup(entry, maxval, gap):
    entry.configure(state= 'normal')

    cur = int(entry.get())
    new = 0
    if cur + gap > maxval:
        new = cur
    else:
        new = cur + gap
        
    entry.delete(0, 'end')    
    entry.insert(0, str(new))
    entry.configure(state= 'readonly')

#정상 범위 설정 창에서 Entry객체의 값을 gap만큼 감소시킴.
#단, 0 미만으로는 감소하지 않음
def entrydown(entry, gap):
    entry.configure(state= 'normal')
    
    cur = int(entry.get())
    new = 0
    if cur - gap < 0:
        new = cur
    else:
        new = cur - gap
    
    entry.delete(0, 'end')
    entry.insert(0, str(new))
    entry.configure(state= 'readonly')   

#정상 범위 설정창에서 설정한 값을 저장
def saveset():
    global alert_set, val_set
    
    option = Radio1.get()
    
    temp_low = text_temp_low.get()
    temp_high = text_temp_high.get()
    hum_low = text_hum_low.get()
    hum_high = text_hum_high.get()
    dust_val = int(text_dust.get())
    mdust_val = int(text_mdust.get())
    
    #'A이상 B이하' 에서 A>B일 경우
    if (int(temp_low) > int(temp_high)) or (int(hum_low) > int(hum_high)):
        tkinter.messagebox.showerror('오류', '온도 또는 습도 범위 설정이 잘못되었습니다.')
        return -1
    
    alert_set = option
    
    name = 'custom'
    temp_val = temp_low + '-' + temp_high
    hum_val = hum_low + '-' + hum_high
    
    vals_new = [name, temp_val, hum_val, dust_val, mdust_val]
    val_set.loc[1] = vals_new
    
    val_set.to_csv(val_set_file, index= False)
    
    return 1
        
#정상범위 설정창 로드시 Entry 객체 초기화
def initialentry():
    global val_set
    
    idx= 1
    
    temp_val = val_set.loc[idx, 'temp']
    temp_val = temp_val.split('-')
    temp_low = temp_val[0]
    temp_high = temp_val[1]
    
    hum_val = val_set.loc[idx, 'hum']
    hum_val = hum_val.split('-')
    hum_low = hum_val[0]
    hum_high = hum_val[1]
    
    dust_val = str(val_set.loc[idx, 'dust'])
    mdust_val = str(val_set.loc[idx, 'mdust'])
    
    setentrynormal()
    
    text_temp_low.delete(0, 'end')
    text_temp_high.delete(0, 'end')
    text_hum_low.delete(0, 'end')
    text_hum_high.delete(0, 'end')
    text_dust.delete(0, 'end')
    text_mdust.delete(0, 'end')
    
    text_temp_low.insert(0, temp_low)
    text_temp_high.insert(0, temp_high)
    text_hum_low.insert(0, hum_low)
    text_hum_high.insert(0, hum_high)
    text_dust.insert(0, dust_val)
    text_mdust.insert(0, mdust_val)
    
    setentryreadonly()

#정상범위 설정 창을 닫고 메인 창을 불러옴
def closesetframe():
    result = saveset()
    if result == -1:
        return
    openFrame(MainFrame)

#정상범위 설정 창을 불러옴
def loadSetframe():
    initialentry()
    openFrame(SetFrame)

#통계 창에서 콤보박스를 초기화
def init_combo():
    global df
    global val_year
    df = pd.read_csv('./' + data)
    df.dropna(inplace= True)
    df['date'] = pd.to_datetime(df['date'])

    years = df['date'].dt.year
    years.drop_duplicates(inplace= True)
    val_year = list(years)
    combo_year.configure(value = val_year)

#통계 창을 불러옴
def load_statframe():
    openFrame(StatFrame)
    init_combo()

#통계 창 화면에 지정된 월 또는 일의 통계치를 표시
def plot():
    global df
    
    source = df.copy()
    tp = combo_type.get()
    year = combo_year.get()
    month = combo_month.get()
    day = combo_date.get()
    
    if tp == '':
        return
    elif tp == '월별':
        if year == '' or month == '':
            return
    elif tp == '날짜별':
        if year == '' or month == '' or day == '':
            return
    
    if tp == '월별':
        start = year + '-01-01'
        end = year + '-12-31'
        
        source.drop('time', axis= 1, inplace= True)
        source = source[source['date'].between(start, end)]
        source['month'] = source['date'].dt.month
        
        df_avg = source.groupby(by= 'month', as_index= False).mean()
        df_avg = df_avg.loc[df_avg['month'] == int(month)]
        
        df_max = source.groupby(by= 'month', as_index= False).max()
        df_max = df_max.loc[df_max['month'] == int(month)]
        
        df_min = source.groupby(by= 'month', as_index= False).min()
        df_min = df_min.loc[df_min['month'] == int(month)]
    
    elif tp == '날짜별':
        source.drop('time', axis= 1, inplace= True)
        source = source.loc[(source['date'].dt.year == int(year)) & (source['date'].dt.month == int(month))]
        source['day'] = source['date'].dt.day
        
        df_avg = source.groupby(by= 'day', as_index= False).mean()
        df_avg = df_avg.loc[df_avg['day'] == int(day)]
        
        df_max = source.groupby(by= 'day', as_index= False).max()
        df_max = df_max.loc[df_max['day'] == int(day)]
        
        df_min = source.groupby(by= 'day', as_index= False).min()
        df_min = df_min.loc[df_min['day'] == int(day)]

    temp_avg = round(df_avg['temp'].values[0], 1)
    hum_avg = round(df_avg['hum'].values[0], 1)
    dust_avg = round(df_avg['dust'].values[0], 1)
    mdust_avg = round(df_avg['mdust'].values[0], 1)
    
    temp_max = round(df_max['temp'].values[0], 1)
    hum_max = round(df_max['hum'].values[0], 1)
    dust_max = round(df_max['dust'].values[0], 1)
    mdust_max = round(df_max['mdust'].values[0], 1)
    
    temp_min = round(df_min['temp'].values[0], 1)
    hum_min = round(df_min['hum'].values[0], 1)
    dust_min = round(df_min['dust'].values[0], 1)
    mdust_min = round(df_min['mdust'].values[0], 1)
    
    dust_info_avg = getDustInfo(dust_avg)
    mdust_info_avg = getMdustInfo(mdust_avg)
    dust_info_max = getDustInfo(dust_max)
    mdust_info_max = getMdustInfo(mdust_max)
    dust_info_min = getDustInfo(dust_min)
    mdust_info_min = getMdustInfo(mdust_min)
    
    slabel_temp.configure(text = str(temp_avg) + 'ºC', fg = getTmpColor(temp_avg), font = font_data_stat)
    slabel_hum.configure(text = str(hum_avg) + '%', font = font_data_stat)
    slabel_dust.configure(text = str(dust_avg) + '㎍/m³', fg = dust_info_avg[1], font = font_data_stat)
    slabel_mdust.configure(text = str(mdust_avg) + '㎍/m³', fg = mdust_info_avg[1], font = font_data_stat)
    
    slabel_temp_max.configure(text = str(temp_max) + 'ºC', fg = getTmpColor(temp_max), font = font_data_stat)
    slabel_hum_max.configure(text = str(hum_max) + '%', font = font_data_stat)
    slabel_dust_max.configure(text = str(dust_max) + '㎍/m³', fg = dust_info_max[1], font = font_data_stat)
    slabel_mdust_max.configure(text = str(mdust_max) + '㎍/m³', fg = mdust_info_max[1], font = font_data_stat)
    
    slabel_temp_min.configure(text = str(temp_min) + 'ºC', fg = getTmpColor(temp_min), font = font_data_stat)
    slabel_hum_min.configure(text = str(hum_min) + '%', font = font_data_stat)
    slabel_dust_min.configure(text = str(dust_min) + '㎍/m³', fg = dust_info_min[1], font = font_data_stat)
    slabel_mdust_min.configure(text = str(mdust_min) + '㎍/m³', fg = mdust_info_min[1], font = font_data_stat)

#통계 기준이 '월별'이면 '일'을 설정하는 콤보박스를 비활성화
def typecontrol(opt):
    if opt == '월별':
        combo_date.configure(state= 'disable')
        button_date.configure(state= 'disable')
    else:
        combo_date.configure(state= 'readonly')
        button_date.configure(state= 'normal')

#'월' 콤보박스 초기화
def setmonth(year):
    global df
    global val_month
    
    filtered = df.loc[df['date'].dt.year == int(year)]
    months = filtered['date'].dt.month
    months.drop_duplicates(inplace= True)
    
    val_month = list(months)
    combo_month.configure(value= val_month)

#'일' 콤보박스 초기화
def setdate(month):
    global df
    global val_date
    
    year = combo_year.get()
    
    filtered = df.loc[(df['date'].dt.year == int(year)) & (df['date'].dt.month == int(month))]
    dates = filtered['date'].dt.day
    dates.drop_duplicates(inplace= True)
    
    val_date = list(dates)
    combo_date.configure(value= val_date)

def combotype():
    global val_type
    
    cur = combo_type.get()
    
    try:
        index = val_type.index(cur)
        if index == len(val_type)-1:
            index= 0
        else:
            index= index + 1
    except:
        index = 0
    
    val = val_type[index]
    combo_type.set(val)
    typecontrol(val)

def comboyear():
    global val_year
    
    cur = combo_year.get()
    if cur != '':
        cur = int(cur)
    
    try:
        index = val_year.index(cur)
        if index == len(val_year)-1:
            index= 0
        else:
            index= index + 1
    except:
        index = 0
    
    val = val_year[index]
    combo_year.set(val)
    setmonth(val)

def combomonth():
    global val_month
    
    cur = combo_month.get()
    if cur != '':
        cur = int(cur)
        
    try:
        index = val_month.index(cur)
        if index == len(val_month)-1:
            index= 0
        else:
            index= index + 1
    except:
        index = 0
    
    val = val_month[index]
    combo_month.set(val)
    setdate(val)
    
def combodate():
    global val_date
    
    cur = combo_date.get()
    if cur != '':
        cur = int(cur)
        
    try:
        index = val_date.index(cur)
        if index == len(val_date)-1:
            index= 0
        else:
            index= index + 1
    except:
        index = 0
    
    val = val_date[index]
    combo_date.set(val)

#메인 화면 상단의 시간을 업데이트
def date():
    weekday_dict = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
    now = dt.datetime.now()
    text = now.strftime('%Y-%m-%d') + ' (' + weekday_dict[now.weekday()] + ') ' + now.strftime('%H:%M')
    label_top.configure(text = text)
    label_top.after(1000, date)

#센서에서 읽어온 값을 파일에 기록하고 저장
def write_data(temp, hum, dust, mdust):
    now = dt.datetime.now()
    
    date = now.strftime('%Y-%m-%d')
    time = now.strftime('%H:%M:%S')
    
    val = [date, time, temp, hum, dust, mdust]
    airdata.loc[airdata.shape[0]] = val
    airdata.reset_index(inplace= True, drop= True)
    
    airdata.to_csv(file, index= False)

#센서에서 값을 일겅온 후 메인 화면에 표시되는 각 수치를 업데이트
def update_data():
    while True: #센서에서 값을 읽을 때 오류가 발생하는 경우가 있으므로 정상적으로 읽을 때까지 반복
        try:
            humidity_data = mydht.humidity #습도
            temperature_data = mydht.temperature #온도
            dust_data = 0
            mdust_data = 0
            buffer = ser.read(1024)
            
            if (dust.protocol_chk(buffer)): #데이터가 유효한지 검사
                data = dust.unpack_data(buffer)
                
                dust_data = data[dust.DUST_PM10_0_ATM] #미세먼지
                mdust_data = data[dust.DUST_PM2_5_ATM] #초미세먼지
                dust_info = getDustInfo(dust_data) #화면에 표시하는데 필요한 정보를 불러옴
                mdust_info = getMdustInfo(mdust_data)
            else:
                print ('data read Err')

            #각 수치가 지정된 정상 범위를 벗어났는지 검사
            alert_state = getAlert(temperature_data, humidity_data, dust_data, mdust_data)
            alert_color = ['blue', 'black', 'red']
            alert_text = ['●', '', '●']

            #화면에 표시되는 텍스트 업데이트
            label_temp.configure(text = str(temperature_data) + '℃', fg= getTmpColor(temperature_data))
            label_hum.configure(text = str(humidity_data) + '%')
            label_dust.configure(text = str(dust_data) + '㎍/m³', fg= dust_info[1])
            label_mdust.configure(text = str(mdust_data) + '㎍/m³', fg= mdust_info[1])
            label_dust_stat.configure(text = dust_info[0], fg= dust_info[1])
            label_mdust_stat.configure(text= mdust_info[0], fg= mdust_info[1])
            
            label_temp_alert.configure(text = alert_text[alert_state[0]+1], fg= alert_color[alert_state[0]+1])
            label_hum_alert.configure(text = alert_text[alert_state[1]+1], fg= alert_color[alert_state[1]+1])
            label_dust_alert.configure(text = alert_text[alert_state[2]+1], fg= alert_color[alert_state[2]+1])
            label_mdust_alert.configure(text = alert_text[alert_state[3]+1], fg= alert_color[alert_state[3]+1])
            
            label_temp.after(update_time* 1000, update_data) #1000ms 후에 이 함수를 다시 호출
            write_data(temperature_data, humidity_data, dust_data, mdust_data) #파일에 데이터를 기록
            
            break
        except: #값을 읽을 때 오류가 발생하면 다시 시도
            continue


#웹페이지 html 파일에 값을 전달하기 위한 함수
@app.route('/get_data')
def get_data():
    idx = airdata.shape[0]-1
    hum = airdata.loc[idx, 'hum']
    temp = airdata.loc[idx, 'temp']
    dust = airdata.loc[idx, 'dust']
    mdust = airdata.loc[idx, 'mdust']
    
    alert_state = getAlert(temp, hum, dust, mdust)
    alert_color = ['blue', 'black', 'red']
    alert_text = ['●', '', '●']
    
    state = [(alert_text[i+1], alert_color[i+1]) for i in alert_state]
    
    return render_template('get_data.html', hum= hum, temp= temp, dust= dust, mdust= mdust, state= state)

def init_func():
    date()
    update_data()

#웹페이지 서버 가동
def run_flask():
    app.run(host= '0.0.0.0')

#tkinter와 웹페이지를 병렬처리하기 위함
def init_flask():
    t1 = Thread(target = run_flask)
    t1.daemon = True
    t1.start()
    
def close(event):
    ser.close()
    root.destroy()


##UI 구성##
#창 객체
root = Tk()
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

#폰트
font_title = Font(family= '맑은 고딕', size= 25)
font_data_title = Font(family= '맑은 고딕', size = 20, weight= 'bold')
font_data_title_stat = Font(family= '맑은 고딕', size= 15, weight= 'bold')
font_data = Font(family= '맑은 고딕', size= 40, weight= 'bold')
font_data_stat = Font(family= '맑은 고딕', size= 20, weight= 'bold')
font_stat = Font(family= '맑은 고딕', size= 15, weight= 'bold')
font_chn = Font(family= '맑은 고딕', size= 20, weight= 'bold')
font_button2 = Font(family= '맑은 고딕', size= 20)
font_button = Font(family= '맑은 고딕', size= 15)
font_combo = Font(family= '맑은 고딕', size= 15)
font_alert = Font(family= '맑은 고딕', size= 50)
font_set = Font(family= '맑은 고딕', size= 17)
font_set_val = Font(family= '맑은 고딕', size= 17)

#아이콘 크기
icon_size = 64
icon_size_stat = 48
icon_size_menu = 32

val_type = ['월별', '날짜별']
val_year = []
val_month = []
val_date = []

#정상범위 설정창, 통계창, 메인화면창
SetFrame = Frame(root)
StatFrame = Frame(root)
MainFrame = Frame(root)

SetFrame.grid(row=0, column=0, sticky= 'nsew')
StatFrame.grid(row=0, column=0, sticky='nsew')
MainFrame.grid(row=0, column=0, sticky='nsew')

##메인화면
#상단 프레임
frame1 = Frame(MainFrame)
frame1.pack(side = 'top', fill = 'both', expand= True)

#상단 표시란(날짜 및 시간)
frame_sub = Frame(frame1)
frame_sub.pack(side = 'top', fill = 'both', expand = True)
frame_sub.columnconfigure(0, weight= 8)
frame_sub.columnconfigure(1, weight= 1)
frame_sub.columnconfigure(2, weight= 1)

text_top = '0000년 00월 00일 (금) 00:00'
label_top = Label(frame_sub, text = text_top, font= font_title, padx = 70, pady= 10)

#웹페이지 주소 안내 버튼  
pic_internet= PhotoImage(file= './internet.png')
icon_internet = pic_internet.subsample(int(pic_internet.width() / icon_size_menu))
button_menu = Button(frame_sub, image= icon_internet, command= msgbox_internet)

#정상범위 설정 버튼
pic_setting= PhotoImage(file= './setting.png')
icon_setting= pic_setting.subsample(int(pic_setting.width() / icon_size_menu))
button_setting = Button(frame_sub, image= icon_setting, command= loadSetframe)

label_top.grid(row= 0, column= 0)
button_setting.grid(row=0, column= 1)
button_menu.grid(row= 0, column= 2)

#구분선
s_top = ttk.Separator(frame1, orient='horizontal')
s_top.pack(fill = 'both', expand= True)

#중간 프레임
frame2 = Frame(MainFrame, pady = 5)
frame2.pack(side = 'top', fill = 'both', expand = True)
for i in range(0,8):
    frame2.columnconfigure(i, weight=1)

#아이콘
pic_temp = PhotoImage(file= './temp.png')
pic_hum = PhotoImage(file= './hum.png')
pic_dust = PhotoImage(file= './dust.png')
pic_mdust = PhotoImage(file= './mdust.png')

icon_temp = pic_temp.subsample(int(pic_temp.width() / icon_size))
icon_hum = pic_hum.subsample(int(pic_hum.width() / icon_size))
icon_dust = pic_dust.subsample(int(pic_dust.width() / icon_size))
icon_mdust = pic_mdust.subsample(int(pic_mdust.width() / icon_size))

icon_temp_stat = pic_temp.subsample(int(pic_temp.width() / icon_size_stat))
icon_hum_stat = pic_hum.subsample(int(pic_hum.width() / icon_size_stat))
icon_dust_stat = pic_dust.subsample(int(pic_dust.width() / icon_size_stat))
icon_mdust_stat = pic_mdust.subsample(int(pic_mdust.width() / icon_size_stat))

label_temp_icon = Label(frame2, image = icon_temp)
label_hum_icon = Label(frame2, image= icon_hum)
label_dust_icon = Label(frame2, image= icon_dust)
label_mdust_icon = Label(frame2, image= icon_mdust)

#항목 이름
label_temp_title = Label(frame2, text = '온도', font= font_data_title, padx = 7, pady = 30)
label_hum_title = Label(frame2, text= '습도', font= font_data_title, padx= 7, pady = 30)
label_dust_title = Label(frame2, text= '미세먼지', font= font_data_title, padx= 7, pady = 30)
label_mdust_title = Label(frame2, text= '초미세먼지', font= font_data_title, padx= 7, pady = 30)
label_temp_title['fg'] = '#e8760c'
label_hum_title['fg'] = '#349eeb'
label_dust_title['fg'] = '#636363'
label_mdust_title['fg'] = '#636363'

label_temp_icon.grid(row= 0, column= 0, sticky= 'e')
label_temp_title.grid(row= 0, column= 1, sticky = 'w')

label_hum_icon.grid(row= 0, column= 2, sticky= 'e')
label_hum_title.grid(row= 0, column= 3, sticky= 'w')

label_dust_icon.grid(row= 0, column= 4, sticky= 'e')
label_dust_title.grid(row=0, column= 5, sticky= 'w')

label_mdust_icon.grid(row= 0, column= 6, sticky= 'e')
label_mdust_title.grid(row= 0, column= 7, sticky= 'w')

#항목별 수치 표시란
label_temp = Label(frame2, text = '30ºC', font= font_data, pady= 30)
label_hum = Label(frame2, text = '65%', font= font_data, pady= 30)
label_dust = Label(frame2, text= '9㎍/m³', font= font_data, fg= 'green', pady= 30)
label_mdust = Label(frame2, text= '8㎍/m³', font= font_data, fg= 'green', pady= 30)

label_temp.grid(row=1, column=0, columnspan= 2)
label_hum.grid(row=1, column=2, columnspan= 2)
label_dust.grid(row=1, column=4, columnspan= 2)
label_mdust.grid(row= 1, column= 6, columnspan= 2)

#미세먼지의 좋음, 보통 등 상태 표시란
label_dust_stat = Label(frame2, text= '좋음', font= font_stat, pady= 15, fg= 'green')
label_mdust_stat = Label(frame2, text= '좋음', font= font_stat, pady= 15, fg= 'green')

label_dust_stat.grid(row= 2, column= 4, columnspan= 2)
label_mdust_stat.grid(row= 2, column= 6, columnspan= 2)

#경고등
label_temp_alert = Label(frame2, text= '●', font= font_alert, fg= 'red')
label_hum_alert = Label(frame2, text= '●', font= font_alert, fg= 'red')
label_dust_alert = Label(frame2, text= '●', font= font_alert, fg= 'red')
label_mdust_alert = Label(frame2, text= '●', font= font_alert, fg= 'red')

label_temp_alert.grid(row= 3, column= 0, columnspan= 2)
label_hum_alert.grid(row= 3, column= 2, columnspan= 2)
label_dust_alert.grid(row= 3, column= 4, columnspan= 2)
label_mdust_alert.grid(row= 3, column= 6, columnspan= 2)

#구분선
s_bottom = ttk.Separator(MainFrame, orient= 'horizontal')
s_bottom.pack(fill = 'both', expand= True)

#하단 프레임
frame3 = Frame(MainFrame, pady= 5)
frame3.pack(side= 'bottom', fill= 'both', expand= True)

#통계창 로딩 버튼
btn_stat = Button(frame3, text= '통계', padx= 20, font= font_button2,
                  command= load_statframe)
btn_stat.pack()


##정상범위 설정 프레임
setframe_title = Frame(SetFrame)
setframe_title.pack(fill= 'both', expand= True)

label_set_title = Label(setframe_title, text= '정상수치 범위 설정', font= font_title, pady= 10)
label_set_title.pack(anchor= 'center', expand= True, fill= 'both')

s_top_set = ttk.Separator(SetFrame, orient='horizontal')
s_top_set.pack(fill = 'both', expand= True)

setframe_top = Frame(SetFrame, pady= 5)
setframe_top.pack(fill = 'both', expand= True)

Radio1 = tkinter.IntVar()

radio_basic = Radiobutton(setframe_top, text="기본 설정", font= font_set, value= 0, variable= Radio1, pady= 3)
radio_custom = Radiobutton(setframe_top, text="사용자 지정 설정:", font= font_set, value= 1, variable= Radio1, pady= 3)

radio_basic.pack(anchor= 'w')
radio_custom.pack(anchor= 'w')

setframe_outside = Frame(SetFrame)
setframe_outside.pack(fill = 'both', expand= True)
setframe = Frame(setframe_outside, padx= 10, pady= 10, relief= 'groove', borderwidth=1)
setframe.pack()

for i in range(0, 8):
    setframe.columnconfigure(i, weight= 1)

label_temp_set = Label(setframe, text= "온도: ", font= font_set, pady= 3)
label_hum_set = Label(setframe, text= "습도: ", font= font_set, pady= 3)
label_dust_set = Label(setframe, text= "미세먼지: ", font= font_set, pady= 3)
label_mdust_set = Label(setframe, text= "초미세먼지: ", font= font_set, pady= 3)
label_range1 = Label(setframe, text= " ~ ", font= font_set, pady= 3)
label_range2 = Label(setframe, text= " ~ ", font= font_set, pady= 3)
label_under1 = Label(setframe, text= "이하", font= font_set, pady= 3)
label_under2 = Label(setframe, text= "이하", font= font_set, pady= 3)

text_temp_low = Entry(setframe, font= font_set_val, state= 'readonly',
                      readonlybackground= 'white',justify= 'center', width= 10)
text_temp_high = Entry(setframe, font= font_set_val, state= 'readonly',
                       readonlybackground= 'white',justify= 'center',  width= 10)
text_hum_low = Entry(setframe, font= font_set_val, state= 'readonly',
                     readonlybackground= 'white',justify= 'center',  width= 10)
text_hum_high = Entry(setframe, font= font_set_val, state= 'readonly',
                      readonlybackground= 'white',justify= 'center',  width= 10)
text_dust = Entry(setframe, font= font_set_val, state= 'readonly',
                  readonlybackground= 'white',justify= 'center',  width= 10)
text_mdust = Entry(setframe, font= font_set_val, state= 'readonly',
                   readonlybackground= 'white',justify= 'center',  width= 10)

rpdelay= 500
rpinterval= 150
btn_temp_low_up = Button(setframe, text='▲', font= font_set,
                         command= lambda: [entryup(text_temp_low, 50, 1)],
                         repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_temp_low_down = Button(setframe, text='▼', font= font_set,
                           command= lambda: [entrydown(text_temp_low, 1)],
                           repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_temp_high_up = Button(setframe, text='▲', font= font_set,
                          command= lambda: [entryup(text_temp_high, 50, 1)],
                          repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_temp_high_down = Button(setframe, text='▼', font= font_set,
                            command= lambda: [entrydown(text_temp_high, 1)],
                            repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_hum_low_up = Button(setframe, text='▲', font= font_set,
                        command= lambda: [entryup(text_hum_low, 100, 5)],
                        repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_hum_low_down = Button(setframe, text='▼', font= font_set,
                          command= lambda: [entrydown(text_hum_low, 5)],
                          repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_hum_high_up = Button(setframe, text='▲', font= font_set,
                         command= lambda: [entryup(text_hum_high, 100, 5)],
                         repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_hum_high_down = Button(setframe, text='▼', font= font_set,
                           command= lambda: [entrydown(text_hum_high, 5)],
                           repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_dust_up = Button(setframe, text='▲', font= font_set,
                     command= lambda: [entryup(text_dust, 150, 5)],
                     repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_dust_down = Button(setframe, text='▼', font= font_set,
                       command= lambda: [entrydown(text_dust, 5)],
                       repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_mdust_up = Button(setframe, text='▲', font= font_set,
                      command= lambda: [entryup(text_mdust, 150, 5)],
                      repeatdelay= rpdelay, repeatinterval= rpinterval)
btn_mdust_down = Button(setframe, text='▼', font= font_set,
                        command= lambda: [entrydown(text_mdust, 5)],
                        repeatdelay= rpdelay, repeatinterval= rpinterval)

#첫째줄
setframe_row_pad = 5
label_temp_set.grid(row=0, column= 0, pady= setframe_row_pad)
btn_temp_low_up.grid(row=0, column= 1, sticky= 'e', pady= setframe_row_pad)
btn_temp_low_down.grid(row=0, column= 2, sticky= 'w', pady= setframe_row_pad)
text_temp_low.grid(row=0, column=3, pady= setframe_row_pad)
label_range1.grid(row=0, column=4, pady= setframe_row_pad)
btn_temp_high_up.grid(row=0, column=5, sticky= 'e', pady= setframe_row_pad)
btn_temp_high_down.grid(row=0, column=6, sticky= 'w', pady= setframe_row_pad) 
text_temp_high.grid(row=0, column=7, pady= setframe_row_pad)

#둘째줄
label_hum_set.grid(row=1, column= 0, pady= setframe_row_pad)
btn_hum_low_up.grid(row=1, column= 1, sticky= 'e', pady= setframe_row_pad)
btn_hum_low_down.grid(row=1, column= 2, sticky= 'w', pady= setframe_row_pad)
text_hum_low.grid(row=1, column=3, pady= setframe_row_pad)
label_range2.grid(row=1, column=4, pady= setframe_row_pad)
btn_hum_high_up.grid(row=1, column=5, sticky= 'e', pady= setframe_row_pad)
btn_hum_high_down.grid(row=1, column=6, sticky= 'w', pady= setframe_row_pad)
text_hum_high.grid(row=1, column=7, pady= setframe_row_pad)

#셋째줄
label_dust_set.grid(row=2, column= 0, pady= setframe_row_pad)
btn_dust_up.grid(row=2, column= 1, sticky= 'e', pady= setframe_row_pad)
btn_dust_down.grid(row=2, column=2, sticky= 'w', pady= setframe_row_pad)
text_dust.grid(row=2, column= 3, pady= setframe_row_pad)
label_under1.grid(row=2, column= 4, pady= setframe_row_pad)

#넷째줄
label_mdust_set.grid(row=3, column= 0, pady= setframe_row_pad)
btn_mdust_up.grid(row=3, column= 1, sticky= 'e', pady= setframe_row_pad)
btn_mdust_down.grid(row=3, column=2, sticky= 'w', pady= setframe_row_pad)
text_mdust.grid(row=3, column= 3, pady= setframe_row_pad)
label_under2.grid(row=3, column= 4, pady= setframe_row_pad)

s_bottom_set = ttk.Separator(SetFrame, orient='horizontal')
s_bottom_set.pack(fill = 'both', expand= True)

#하단 프레임
setframe_bottom = Frame(SetFrame, pady= 5)
setframe_bottom.pack(side= 'bottom', fill='both', expand= True)

#저장 및 메인화면 전환 버튼
btn_save = Button(setframe_bottom, text= '저장', font= font_button2, padx= 10,
                  command= closesetframe)
btn_save.pack()


#통계창 프레임
statframe1 = Frame(StatFrame, pady= 10)
statframe1.pack(side= 'top', fill= 'both', expand= True)
for i in range(0,9):
    statframe1.columnconfigure(i, weight= 1)

    
types = ['월별', '날짜별']

combo_type = ttk.Combobox(statframe1, state= 'readonly', width= 10, value= types, font= font_combo)
combo_year = ttk.Combobox(statframe1, state= 'readonly', width = 10, font= font_combo)
combo_month = ttk.Combobox(statframe1, state= 'readonly', width= 5, font= font_combo)
combo_date = ttk.Combobox(statframe1, state= 'readonly', width= 5, font= font_combo)
btn_stat = Button(statframe1, text= '확인', padx= 7, font= font_button,
                  command= plot)

#콤보박스 조작 버튼. 터치스크린에서 콤보박스가 터치로 선택되지 않기 때문에 버튼으로 대체.
button_type = Button(statframe1, text= '기준▲', font= font_button, command= combotype)
button_year = Button(statframe1, text= '년도▲', font= font_button, command= comboyear)
button_month = Button(statframe1, text= '월▲', font= font_button, command= combomonth)
button_date = Button(statframe1, text= '일▲', font= font_button, command= combodate)

button_type.grid(row=0, column= 0)
combo_type.grid(row=0, column= 1, padx= 3)
button_year.grid(row=0, column= 2)
combo_year.grid(row=0, column= 3, padx= 3)
button_month.grid(row=0, column= 4)
combo_month.grid(row=0, column= 5, padx= 3)
button_date.grid(row=0, column= 6)
combo_date.grid(row=0, column= 7, padx= 3)
btn_stat.grid(row=0, column= 8, padx = 10)

s_top = ttk.Separator(StatFrame, orient= 'horizontal')
s_top.pack(side= 'top', fill= 'both', expand= True)

#중간 프레임
statframe2 = Frame(StatFrame, pady = 5)
statframe2.pack(side = 'top', fill = 'both', expand = True)
for i in range(0,9):
    statframe2.columnconfigure(i, weight=1)

slabel_temp_icon = Label(statframe2, image = icon_temp_stat)
slabel_hum_icon = Label(statframe2, image= icon_hum_stat)
slabel_dust_icon = Label(statframe2, image= icon_dust_stat)
slabel_mdust_icon = Label(statframe2, image= icon_mdust_stat)

slabel_temp_title = Label(statframe2, text = '온도', font= font_data_title_stat, padx = 7, pady = 30)
slabel_hum_title = Label(statframe2, text= '습도', font= font_data_title_stat, padx= 7, pady = 30)
slabel_dust_title = Label(statframe2, text= '미세먼지', font= font_data_title_stat, padx= 7, pady = 30)
slabel_mdust_title = Label(statframe2, text= '초미세먼지', font= font_data_title_stat, padx= 7, pady = 30)
slabel_temp_title['fg'] = '#e8760c'
slabel_hum_title['fg'] = '#349eeb'
slabel_dust_title['fg'] = '#636363'
slabel_mdust_title['fg'] = '#636363'

slabel_avg = Label(statframe2, text= '평균', font= font_button)
slabel_max = Label(statframe2, text= '최고', font= font_button)
slabel_min = Label(statframe2, text= '최저', font= font_button)

slabel_temp_icon.grid(row= 0, column= 1, sticky= 'e')
slabel_temp_title.grid(row= 0, column= 2, sticky = 'w')

slabel_hum_icon.grid(row= 0, column= 3, sticky= 'e')
slabel_hum_title.grid(row= 0, column= 4, sticky= 'w')

slabel_dust_icon.grid(row= 0, column= 5, sticky= 'e')
slabel_dust_title.grid(row=0, column= 6, sticky= 'w')

slabel_mdust_icon.grid(row= 0, column= 7, sticky= 'e')
slabel_mdust_title.grid(row= 0, column= 8, sticky= 'w')

slabel_temp = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_hum = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_dust = Label(statframe2, text= '-', font= font_data_stat, pady= 20)
slabel_mdust = Label(statframe2, text= '-', font= font_data_stat, pady= 20)

slabel_temp_max = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_hum_max = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_dust_max = Label(statframe2, text= '-', font= font_data_stat, pady= 20)
slabel_mdust_max = Label(statframe2, text= '-', font= font_data_stat, pady= 20)

slabel_temp_min = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_hum_min = Label(statframe2, text = '-', font= font_data_stat, pady= 20)
slabel_dust_min = Label(statframe2, text= '-', font= font_data_stat, pady= 20)
slabel_mdust_min = Label(statframe2, text= '-', font= font_data_stat, pady= 20)

slabel_avg.grid(row=1, column=0)
slabel_temp.grid(row=1, column=1, columnspan= 2)
slabel_hum.grid(row=1, column=3, columnspan= 2)
slabel_dust.grid(row=1, column=5, columnspan= 2)
slabel_mdust.grid(row= 1, column= 7, columnspan= 2)

slabel_max.grid(row=2, column=0)
slabel_temp_max.grid(row=2, column=1, columnspan= 2)
slabel_hum_max.grid(row=2, column=3, columnspan= 2)
slabel_dust_max.grid(row=2, column=5, columnspan= 2)
slabel_mdust_max.grid(row=2, column= 7, columnspan= 2)

slabel_min.grid(row=3, column=0)
slabel_temp_min.grid(row=3, column=1, columnspan= 2)
slabel_hum_min.grid(row=3, column=3, columnspan= 2)
slabel_dust_min.grid(row=3, column=5, columnspan= 2)
slabel_mdust_min.grid(row=3, column= 7, columnspan= 2)

s_bottom = ttk.Separator(StatFrame, orient= 'horizontal')
s_bottom.pack(side= 'top', fill= 'both', expand= True)

#하단 프레임
statframe3 = Frame(StatFrame, pady= 10)
statframe3.pack(side= 'bottom', fill= 'both', expand= True)

#메인화면 전환 버튼
btn_back = Button(statframe3, text= '뒤로', padx= 7, font= font_button2,
                  command= lambda:[openFrame(MainFrame)])
btn_back.pack()

#초기화
init_func()
init_flask()

#창 실행
root.attributes('-fullscreen', True)
root.bind('<F11>', lambda event: root.attributes('-fullscreen', False))
root.bind('<Escape>', close)
root.option_add('*TCombobox*Listbox*Font', font_combo)
root.mainloop()
