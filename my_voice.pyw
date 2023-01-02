#!/usr/bin/env python3
"""
автор программы: Султанов Искандер (BigIskander@gmail.com)
подробнее о программе:
https://iskandersultanov.wordpress.com/my_voice/
"""
#импортируем нужные библиотеки
import os
import sys
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as msgb
import webbrowser
#библиотека плейера vlc
try:
    import vlc
except:
    msgb.showinfo(message="VLC media player не установлен!")
    sys.exit()
#для отображения времени воспроизведения
from datetime import timedelta

#библиотеки для записи голоса
import sounddevice as sd
import queue
import soundfile as sf
import threading
#import numpy

#print(numpy.__file__)

#VLC - Player
Instance=vlc.Instance()
player=Instance.media_player_new()
Instance2=vlc.Instance()
player2=Instance2.media_player_new()

#для компиляции с pyinstaller
if getattr(sys, 'frozen', False):
    cdir = os.path.dirname(sys.executable)
else:
    cdir = os.path.dirname(os.path.abspath(__file__))

#параметы видео
video_is_opened=False
video=""
open_retry=0
video_lenght=0
video_f="0:00:00"
video_t="0:00:00"
video_p="0:00:00"
speed_prev=1.00

#параметры записи аудио
is_recording=False
rec_file_name="my_voice.wav"
is_recorded=False
rec_open_retry=0
rec_lenght=0
rec_f="0:00:00"
rec_t="0:00:00"
rec_p="0:00:00"
rec_is_opened=False
q=queue.Queue()

#воспроизвести оба
is_play_both=False
on_start=True

#сократить название до 40 символов
def name_shorten(name):
    if len(name)<=40:
        return name
    return name[:20]+"..."+name[-20:]

#получить начальные параметры записи
def get_video_info(ft=True):
    global video_lenght
    global video_f
    global video_t
    global open_retry
    global video_is_opened
    global video
    global rec_file_name
    if ft:
        #выключить звук и воспроизвести 100миллисекунд видео или аудио
        #для получения параметров записи
        player.audio_set_mute(True)
        player.play()
        root.after(ms=100, func=lambda: get_video_info(False))
    else:
        #проверка может ли файл быть воспроизведен файл
        #print(player.get_state())
        if not str(player.get_state())=="State.Playing":
            if str(player.get_state())=="State.Opening":
                #ограничения времени ожидание открытия файла
                if open_retry>5:
                    video_is_opened=False
                else:
                    open_retry=open_retry+1
                    #может уйти в бесконечный цикл
                    root.after(ms=100, func=lambda: get_video_info(False))
                    return
            else:
                video_is_opened=False
        else:
            video_is_opened=True
        #в случае попытки открыть файл в который записывает сама программа
        is_rec_file=False
        if os.path.abspath(video)==os.path.abspath(cdir+"/"+rec_file_name):
            video_is_opened=False
            is_rec_file=True
        #
        play_both_d()
        #если не открылось сделать кнопки неактивными
        if not video_is_opened:
            open_retry=0
            player.stop() # release()
            video_name_label["text"]="Образец произношения (видео или аудио): не открыто"
            play_butt['state']="disabled"
            stop_butt['state']="disabled"
            volume_selector.set(100)
            volume_selector['state']="disabled"
            from_to_label['text']="0:00:00 (от: 0:00:00 до: 0:00:00)"
            if not is_rec_file:
                msgb.showinfo(message="Выбранный файл не может быть воспроизведен!")
            else:
                msgb.showinfo(message="Это файл в который осуществляется запись!")
            return
        #если файл может быть воспроизведен продолжить
        if player.is_playing():
            player.pause()
        player.set_time(0)
        player.audio_set_mute(False)
        tempo.set(1.00)
        player.set_rate(1.00)
        # -200мс to fix some issues
        video_lenght=player.get_length() #-200
        sec=int(video_lenght/1000)
        if sec<0:
            sec=0
        video_f=timedelta(seconds=0)
        video_t=timedelta(seconds=sec)
        track()
        time_label()
        video_name_label["text"]="Образец произношения (видео или аудио): '"+name_shorten(os.path.basename(video))+"'"
        #сделать кнопки активными
        volume_selector['state']="normal"
        volume_selector.set(int(player.audio_get_volume()))
        play_butt['state']="normal"
        stop_butt['state']="normal"

#воспроизводить с определенного отрезка
def play():
    if not video_is_opened or is_recording:
        return
    global video_lenght
    global is_play_both
    if player2.is_playing():
        rec_play_stop()
        if is_play_both:
            is_play_both=False
    if player.is_playing():
        player.pause()
        if is_play_both:
            is_play_both=False
        return
    #костыль
    if str(player.get_state())=="State.Ended":
        m = Instance.media_new(str(video))
        player.set_media(m)
        return
    #
    play_coords=selector.coords(2)
    start_coords=selector.coords(3)
    stop_coords=selector.coords(4)
    if play_coords[2]>=stop_coords[0]-20:
        play_coords[2]=start_coords[0]
    start_time=int(video_lenght*(play_coords[2]-21)/510)
    player.play()
    player.set_time(start_time)
    root.after(ms=100, func=lambda: track())

#воспроизводить до заданного момента
def track():
    if not video_is_opened:
        return
    global video_lenght
    global video_p
    global is_play_both
    if video_lenght<=0:
        return
    #отображение воспроизведения на шкале
    play_now=player.get_time()
    play_now_x=21+510*(play_now/video_lenght)
    selector.coords(2, 21, 0, play_now_x, 20)
    #остановить воспроизведение
    stop_coords=selector.coords(4)
    if play_now_x>=stop_coords[0]-20 or video_lenght-play_now<=200:
        if player.is_playing():
            player.pause()
            if is_play_both:
                is_play_both=False
                root.after(ms=100, func=lambda: rec_play())
            return
    #обновить надпись времени
    if player.is_playing():
        #изменение надписи
        sec=int(play_now/1000)
        if sec<0:
            sec=0
        video_p=timedelta(seconds=sec)
        time_label()
        #перезапуск этой функции пока воспроизводится (рекурсия)
        root.after(ms=100, func=lambda: track())

#остановить воспроизведение
def stop():
    if not video_is_opened:
        return
    global video_lenght
    global is_play_both
    is_play_both=False
    start_coords=selector.coords(3)
    start_time=int(video_lenght*(start_coords[0]-21)/510)
    player.set_time(start_time)
    if player.is_playing():
        player.pause()
    track()
    time_label()

#скорость воспроизведения
def video_speed():
    global speed_prev
    #если идет запись ничего не менять
    if is_recording:
        tempo.set(speed_prev)
        return
    speed_prev=tempo.get()
    player.set_rate(speed_prev)

#действие по нажатию кнопки пробел
def space_press():
    if not video_is_opened or is_recording or player2.is_playing():
        return
    play()

#идея с перемещением объектов внутри канваса отсюда
#https://stackoverflow.com/questions/65189412/python-canvas-move-items-with-mouse-tkinter

#выбрать объект для перемещения (выбрать ползунок видео)
def on_click(event):
    #не реагировать если видео не открыто или идет воспроизведение
    if player.is_playing() or not video_is_opened or is_recording:
        return
    #выбрать ползунок
    selected = selector.find_overlapping(event.x, event.y, event.x, event.y)
    if selected:
        selector.selected = selected[-1]
        selector.startxy = (event.x, event.y)
    else:
        selector.selected = None

#переместить ползунок времени видео
def on_drag(event):
    #не реагировать если видео не открыто или идет воспроизведение
    if player.is_playing() or not video_is_opened or is_recording:
        return
    global video_f
    global video_t
    global video_p
    #перемещять ползунок
    if selector.selected in [3, 4]:
        # calculate distance moved from last position
        dx, dy = event.x-selector.startxy[0], 0
        #не выходит за пределы
        coords=selector.coords(selector.selected)
        if coords[0]+dx<22:
            dx=0
        elif coords[0]+dx>550:
            dx=0
        #не пересекают друг друга
        if selector.selected==3:
            op_coords=selector.coords(4)
            if coords[0]+dx>op_coords[0]-20:
                dx=0
            else:
                selector.coords(2, 21, 0, coords[0]+dx, 20)
        elif selector.selected==4:
            op_coords=selector.coords(3)
            if coords[0]+dx<op_coords[0]+20:
                dx=0
        # move the selected item
        selector.move(selector.selected, dx, dy)
        # update last position
        selector.startxy = (event.x, event.y)
        #обновить надпись времени
        if selector.selected==3:
            st_coords=selector.coords(3)
            st=video_lenght*(st_coords[0]+dx-21)/510
            sec=int(st/1000)
            if sec<0:
                sec=0
            video_f=timedelta(seconds=sec)
            video_p=timedelta(seconds=sec)
        elif selector.selected==4:
            st_coords=selector.coords(4)
            st=video_lenght*(st_coords[0]+dx-41)/510
            sec=int(st/1000)
            if sec<0:
                sec=0
            video_t=timedelta(seconds=sec)
        time_label()

#отображение времени воспроизведения видео
def time_label():
    if not video_is_opened:
        return
    global video_f
    global video_t
    global video_p
    from_to_label.config(text=str(video_p)+" (от: "+str(video_f)+" до: "+str(video_t)+")")

#изменение громкости воспроизведения ведио
def volume(event):
    if not video_is_opened:
        return
    player.audio_set_volume(int(event))

#открыть новое видео или аудио
def open_video():
    #если идет запись ничего не открывать
    if is_recording:
        return
    #VLC
    global player
    global video_is_opened
    global video
    global open_retry
    #остановить воспроизведение
    if player.is_playing():
        stop()
    if player2.is_playing():
        rec_play_stop()
    #выбрать и открыть файл
    video= fd.askopenfilename(initialdir=cdir)
    if video=="":
        return
    m = Instance.media_new(str(video))
    player.set_media(m)
    #сбросить при открытии нового видео
    selector.coords(2, 21, 0, 22, 20)
    selector.coords(3, 22, 22, 22, 0, 0, 22)
    selector.coords(4, 550-0, 22, 550-20, 22, 550-20, 0)
    #получить параметры видео
    open_retry=0
    get_video_info()

#аудиозапись голоса, идея взята отсюда
#https://projectgurukul.org/python-voice-recorder-project/

#Fit data into queue
def callback(indata, frames, time, status):
    global q
    q.put(indata.copy())

def record_audio():
    global is_recording
    global is_recorded
    global rec_file_name
    global q
    global rec_lenght
    #если уже пишеться то остановить запись
    if is_recording:
        is_recording=False
        record_button['text']="Записать"
        if os.name == "nt":
            record_button['bg']="SystemButtonFace"
        record_play_button['state']="normal"
        record_play_stop_button['state']="normal"
        record_volume_selector['state']="normal"
        record_label["text"]="Мой голос (my_voice.wav)"
        while_rec_disable(False)
        play_both_d()
        return
    #остановить воспроизведение
    stop()
    rec_play_stop()
    rec_lenght=0
    #запись
    is_recording=True
    record_button['text']="Записывается\nаудио (завершить)"
    if os.name == "nt":
        record_button['bg']="red"
    record_play_button['state']="disabled"
    record_play_stop_button['state']="disabled"
    record_volume_selector['state']="disabled"
    record_label["text"]="Мой голос (my_voice.wav): записывается"
    while_rec_disable(True)
    play_both_d()
    #messagebox.showinfo(message="Recording Audio. Speak into the mic")
    try:
        #создать файл для записи
        with sf.SoundFile(cdir+"/"+rec_file_name, mode='w', samplerate=44100, channels=2) as file:
        #Create an input stream to record audio without a preset time
                with sd.InputStream(samplerate=44100, channels=2, callback=callback):
                    while is_recording==True:
                        file.write(q.get())
                    is_recorded=True
                    open_rec()
    except:
        #если не записывается
        is_recording=False
        is_recorded=False
        record_button['text']="Записать"
        if os.name == "nt":
            record_button['bg']="SystemButtonFace"
        record_play_button['state']="disabled"
        record_play_stop_button['state']="disabled"
        record_volume_selector['state']="disabled"
        record_to_label['text']="0:00:00 (от: 0:00:00 до: 0:00:00)"
        record_label["text"]="Мой голос (my_voice.wav): не записан"
        while_rec_disable(False)
        msgb.showinfo(message="Произошла ошибка: Не удалось записать аудио!")

#запустить запись
def do_record():
    t=threading.Thread(target=record_audio)
    t.start()
    root.after(ms=100, func=lambda: rec_time_label_update())

def while_rec_disable(dis=True):
    if dis and video_is_opened:
        play_butt['state']="disabled"
        stop_butt['state']="disabled"
        volume_selector['state']="disabled"
    else:
        if video_is_opened:
            play_butt['state']="normal"
            stop_butt['state']="normal"
            volume_selector['state']="normal"
    pass

#получить начальные параметры записи
def get_rec_info(ft=True):
    global rec_lenght
    global rec_f
    global rec_t
    global rec_open_retry
    global rec_is_opened
    global rec_file_name
    global on_start
    if ft:
        #выключить звук и воспроизвести 100миллисекунд видео или аудио
        #для получения параметров записи
        player2.audio_set_mute(True)
        player2.play()
        root.after(ms=100, func=lambda: get_rec_info(False))
    else:
        #проверка может ли файл быть воспроизведен файл
        #print(player.get_state())
        if not str(player2.get_state())=="State.Playing":
            if str(player2.get_state())=="State.Opening":
                #ограничения времени ожидание открытия файла
                if rec_open_retry>5:
                    rec_is_opened=False
                else:
                    rec_open_retry=rec_open_retry+1
                    #может уйти в бесконечный цикл
                    root.after(ms=100, func=lambda: get_rec_info(False))
                    return
            else:
                rec_is_opened=False
        else:
            rec_is_opened=True
        #
        play_both_d()
        #если не открылось сделать кнопки неактивными
        if not rec_is_opened:
            rec_open_retry=0
            player2.stop() # release()
            record_label["text"]="Мой голос (my_voice.wav): не записан"
            record_play_button['state']="disabled"
            record_play_stop_button['state']="disabled"
            record_volume_selector.set(100)
            record_volume_selector['state']="disabled"
            record_to_label['text']="0:00:00 (от: 0:00:00 до: 0:00:00)"
            if not on_start:
                msgb.showinfo(message="Произошла ошибка: Не удалось открыть записанный файл!")
            on_start=False
            return
        #если файл может быть воспроизведен продолжить
        on_start=False
        if player2.is_playing():
            player2.pause()
        player2.set_time(0)
        player2.audio_set_mute(False)
        # -200мс для устранения бага
        rec_lenght=player2.get_length()-200
        sec=int(rec_lenght/1000)
        if sec<0:
            sec=0
        rec_f=timedelta(seconds=0)
        rec_t=timedelta(seconds=sec)
        rec_play_track()
        rec_time_label()
        record_label["text"]="Мой голос (my_voice.wav)"
        #сделать кнопки активными
        record_volume_selector['state']="normal"
        record_volume_selector.set(int(player2.audio_get_volume()))
        record_play_button['state']="normal"
        record_play_stop_button['state']="normal"

#воспроизводить с определенного отрезка
def rec_play():
    if not rec_is_opened or is_recording:
        return
    global rec_lenght
    if player.is_playing():
        stop()
    if player2.is_playing():
        rec_play_stop()
    #костыль
    if str(player2.get_state())=="State.Ended":
        open_rec()
        return
    #
    player2.play()
    player2.set_time(0)
    root.after(ms=100, func=lambda: rec_play_track())

#воспроизводить до заданного момента
def rec_play_track():
    if not rec_is_opened:
        return
    global rec_lenght
    global rec_p
    if rec_lenght<=0:
        return
    #отображение воспроизведения на шкале
    play_now=player2.get_time()
    play_now_x=21+510*(play_now/rec_lenght)
    record_play_progress.coords(2, 21, 0, play_now_x, 20)
    #остановить воспроизведение (за 200мс до конца)
    if rec_lenght-play_now<=0:
        if player2.is_playing():
            player2.pause()
            return
    #обновить надпись времени
    if player2.is_playing():
        #изменение надписи
        sec=int(play_now/1000)
        if sec<0:
            sec=0
        rec_p=timedelta(seconds=sec)
        rec_time_label()
        #перезапуск этой функции пока воспроизводится (рекурсия)
        root.after(ms=100, func=lambda: rec_play_track())

#остановить воспроизведение
def rec_play_stop():
    if not rec_is_opened:
        return
    global rec_lenght
    global rec_p
    player2.set_time(0)
    if player2.is_playing():
        player2.pause()
    rec_p="0:00:00"
    rec_play_track()
    rec_time_label()

#отображение времени воспроизведения видео
def rec_time_label():
    if not rec_is_opened and not is_recording:
        return
    global rec_f
    global rec_t
    global rec_p
    record_to_label.config(text=str(rec_p)+" (от: "+str(rec_f)+" до: "+str(rec_t)+")")

#изменение громкости воспроизведения ведио
def rec_volume(event):
    if not rec_is_opened:
        return
    player2.audio_set_volume(int(event))

#открыть новое видео или аудио
def open_rec():
    #если идет запись ничего не открывать
    if is_recording:
        return
    #VLC
    global player2
    m = Instance2.media_new(str(cdir+"/"+rec_file_name))
    player2.set_media(m)
    #сбросить в начало
    record_play_progress.coords(2, 21, 0, 22, 20)
    #получить параметры записи
    open_retry=0
    get_rec_info()

#обновлять надпись по мере записи
def rec_time_label_update():
    global rec_t
    global rec_lenght
    rec_lenght=rec_lenght+100
    sec=int(rec_lenght/1000)
    if sec<0:
        sec=0
    rec_t=timedelta(seconds=sec)
    rec_time_label()
    if is_recording:
        root.after(ms=100, func=lambda: rec_time_label_update())

#воспроизвести ошибка
def play_both():
    #не реагировать если не открыто одно или оба записи или идет запись
    if not rec_is_opened or not video_is_opened or is_recording:
        return
    global is_play_both
    is_play_both=True
    play()
    #msgb.showinfo(message="Ok!")

#определяет активная ли кнопка "воспроизвести оба"
def play_both_d():
    if not rec_is_opened or not video_is_opened or is_recording:
        play_both_button["state"]="disabled"
    else:
        play_both_button["state"]="normal"

#выполнить один раз при запуске программы
def start():
    root.unbind('<Visibility>')
    open_rec()

#на сайт программы
site_link="https://iskandersultanov.wordpress.com/my_voice/"
def about():
    #если идет запись ингнорировать
    if is_recording:
        return
    #остановить воспроизведение
    if player.is_playing():
        stop()
    if player2.is_playing():
        rec_play_stop()
    #кратко о программе
    text="Программа для постановки произношения."
    text=text+"\nАвтор программы: Султанов Искандер (BigIskander@gmail.com)"
    text=text+"\nПерейти на сайт программы?"
    op_site = msgb.askyesno(message=text)
    if op_site:
        webbrowser.open_new(site_link)

#создать окно и задать свойства
root = tk.Tk()
root.title("我学习汉语音")
root.geometry("700x575")
root.resizable(False, False)
root.configure(background="white")
root.bind('<Visibility>', lambda event: start())

#меню открыть
menu=tk.Menu(root)
menu.add_command(label="Открыть видео/аудио", command=open_video)
tempo=tk.DoubleVar()
sub_menu=tk.Menu(menu, tearoff=0)
sub_menu.add_radiobutton(label="0.50", variable=tempo, value=0.50, command=video_speed)
sub_menu.add_radiobutton(label="0.75", variable=tempo, value=0.75, command=video_speed)
sub_menu.add_radiobutton(label="1.00", variable=tempo, value=1.00, command=video_speed)
sub_menu.add_radiobutton(label="1.25", variable=tempo, value=1.25, command=video_speed)
sub_menu.add_radiobutton(label="1.50", variable=tempo, value=1.50, command=video_speed)
tempo.set(1.00)
menu.add_cascade(label="Темп воспроизведения", menu=sub_menu)
menu.add_command(label="О программе", command=about)
root.configure(menu=menu)

#видео/аудио часть дизайна окна
#
video_frame=tk.Frame(root, bg="white")
video_frame.pack(side="top")
video_name_label=tk.Label(video_frame, text="Образец произношения (видео или аудио): не открыто", bg="white")
video_name_label.pack(side="top")
cnvs1=tk.Canvas(video_frame, width=680, height=5, bg="white", highlightthickness=0)
cnvs1.pack()
video_canvas=tk.Canvas(video_frame, height=300, width=510, bg="grey", highlightthickness=0)
video_canvas.pack(side="top")
selector=tk.Canvas(video_frame, height=20, width=550, bg="white", highlightthickness=0)
selector.pack(side="top")
#VLC part
h = video_canvas.winfo_id()
if os.name=="nt":
    player.set_hwnd(h)
else:
    player.set_xwindow(h)
#прогресс воспроизведения
selector.create_rectangle((21,0),(550-19,20),fill="red",width=0)
selector.create_rectangle((21,0),(22,20),fill="green",width=0)
#начало и конец воспроизведения
selector.create_polygon((22,22),(22,0),(0,22),fill="orange",width=0)
selector.create_polygon((550-0,22),(550-20,22),(550-20,0),fill="blue",width=0)
#кнопки воспроизвести остановить
button_frame=tk.Frame(video_frame, bg="white")
from_to_label_frame=tk.Frame(button_frame)
from_to_label=tk.Label(from_to_label_frame, text="0:00:00 (от: 0:00:00 до: 0:00:00)", bg="white", highlightthickness=0)
from_to_label.pack(side="left")
from_to_label_frame.pack(side="top")
play_butt=tk.Button(button_frame, text="Воспроизвести\nПауза", command=play, state="disabled")
stop_butt=tk.Button(button_frame, text="Остановить", command=stop, state="disabled")
play_butt.pack(side="left")
stop_butt.pack(side="left")
button_frame.pack(side="left", fill="x", expand=True)
#привязка нажатий и перемещения мыши к функциям (выбор отрезка воспроизведения)
selector.bind("<Button-1>", on_click)
selector.bind("<B1-Motion>", on_drag)
#регулятор громкости
volume_selector=tk.Scale(button_frame, length=200, command=volume, from_=0, to=100, orient="horizontal",
                                variable=50, bg="white", highlightthickness=0)
volume_selector.set(100)
volume_selector["state"]="disabled"
volume_selector.pack(side="right")
volume_label=tk.Label(button_frame, text="Громкость:", bg="white")
volume_label.pack(side="right")
divide_line=tk.Canvas(root, bg="grey", width=700, height=5)
divide_line.pack()

#часть окна, запись и воспроизведение голоса
my_voice_frame=tk.Frame(root, bg="white")
my_voice_frame.pack(side="top")
record_label=tk.Label(my_voice_frame, text="Мой голос (my_voice.wav): не записан", bg="white")
record_label.pack(side="top")
cnvs2=tk.Canvas(my_voice_frame, width=680, height=5, bg="white", highlightthickness=0)
cnvs2.pack()
record_play_progress=tk.Canvas(my_voice_frame, height=20, width=550, bg="white", highlightthickness=0)
record_play_progress.pack(side="top")
#прогресс воспроизведения
record_play_progress.create_rectangle((21,0),(550-19,20),fill="red",width=0)
record_play_progress.create_rectangle((21,0),(22,20),fill="green",width=0)
#кнопки
my_voice_frame_buttons=tk.Frame(my_voice_frame, bg="white", highlightthickness=0)
my_voice_frame_buttons.pack(fill="x", expand=True)
record_to_label_frame=tk.Frame(my_voice_frame_buttons)
record_to_label=tk.Label(record_to_label_frame, text="0:00:00 (от: 0:00:00 до: 0:00:00)", bg="white", highlightthickness=0)
record_to_label.pack(side="left")
record_to_label_frame.pack(side="top")
record_play_button=tk.Button(my_voice_frame_buttons, text="Воспроизвести", command=rec_play, state="disabled")
record_play_button.pack(side="left")
record_play_stop_button=tk.Button(my_voice_frame_buttons, text="Остановить", command=rec_play_stop, state="disabled")
record_play_stop_button.pack(side="left")
record_button=tk.Button(my_voice_frame_buttons, text="Записать", command=do_record)
record_button.pack(side="left")
record_volume_selector=tk.Scale(my_voice_frame_buttons, length=200, command=rec_volume, from_=0, to=100, orient="horizontal",
                                 bg="white", highlightthickness=0)
record_volume_selector.set(100)
record_volume_selector["state"]="disabled"
record_volume_selector.pack(side="right")

record_volume_label=tk.Label(my_voice_frame_buttons, text="Громкость:", bg="white")
record_volume_label.pack(side="right")
divide_line2=tk.Canvas(root, bg="grey", width=700, height=5)
divide_line2.pack()

#кнопка воспроизвести оба
play_both_frame=tk.Frame(root, bg="white", highlightthickness=0)
play_both_frame.pack()
cnvs3=tk.Canvas(play_both_frame, width=680, height=10, bg="white", highlightthickness=0)
cnvs3.pack()
play_both_button=tk.Button(play_both_frame, text="Воспроизвести оба (сравнить)", command=play_both, state="disabled")
play_both_button.pack(side="top")

#
root.bind("<space>", lambda event: space_press())

#отобразить окно
root.mainloop()
