import sqlite3 ## https://docs.python.org/3/library/sqlite3.html
import PySimpleGUI as sg ## https://www.pysimplegui.org/en/latest/call%20reference
from psgtray import SystemTray
from datetime import date, timedelta
import time

## tables:          logs, tarefas
## logs:            CREATE TABLE logs(id integer primary key autoincrement, dia integer, mes integer, ano integer, inicio real, duracao real, tarefa text);
## tarefas:         CREATE TABLE tarefas(id integer primary key autoincrement, nome text, descricao text, tags text);
## tags format:     '.tag1.tag2'

LOGO = "logo.ico"
EMOJI_RUNNING = '▶️'
EMOJI_PAUSE = '⏸️'

def create_tray_icon(window):
    menu = ['', ['Mostrar janela', 'Esconder Janela', "Sair"]]
    return SystemTray(menu, single_click_events=False, window=window, tooltip='timer', icon=LOGO)


def create_menu_layout():
    return [ ['Tarefas',['Ver tarefas', '!Editar tarefas', 'Adicionar tarefa']], 
            ['Registos', ['Ver registros', '!Editar registos']] ]

def create_layout(tarefas:list):
    menu = [sg.Menu(create_menu_layout())]
    
    l1 = [sg.P(), sg.T(EMOJI_PAUSE, text_color='red', k='emoji'), sg.T('0:00:00', k='tempo'), sg.P()]

    l2 = [sg.P(), sg.Combo(values=tarefas, enable_events=True, readonly=True, k='tarefa'), sg.P()]

    l3 = [sg.P(), sg.pin(sg.B('Começar', k='comecar', disabled=True)), sg.pin(sg.B('Terminar', k='parar', visible=False)), 
          sg.pin(sg.B('Pausar', k='pausar', visible=False)), sg.P()]

    return [menu, [sg.VPush()], l1, l2, l3, [sg.VPush()]]

def adicionar_tarefa(con, cur):
    col1 = [[sg.T('Nome')], [sg.T('Descrição'),], [sg.T('Tags')]] 
    col2 = [[sg.In(k='nome', s=30)], [sg.In(k='descricao', s=30)], [sg.In(k='tags', s=30)]]

    layout = [[sg.Column(col1), sg.Column(col2)],
              [sg.P(), sg.B('Adicionar'), sg.B('Cancelar', k='cancelar'), sg.P()],
              [sg.P(), sg.T('As tags devem ter o formato .tag1.tag2 etc.'), sg.P()]]
    
    event, values = sg.Window('Adicionar tarefa', layout, icon=LOGO).read(close=True)

    if event == 'cancelar' or event == sg.WIN_CLOSED:
        return

    if values['nome'] == '':
        sg.Window('Adicionar tarefa', [[sg.T('O campo nome não pode estar vazio.')], [sg.P(), sg.B('Ok'), sg.P()]], icon=LOGO).read(close=True)
        ## remove comment to open a new window automatically:
        # adicionar_tarefa(con, cur)
        return

    print('A ADICIONAR TAREFA')

    values_to_save = (values['nome'], values['descricao'], values['tags'])
    cur.execute('INSERT INTO tarefas(nome, descricao, tags) VALUES(?, ?, ?)', values_to_save)
    con.commit()
          
def ver_tarefas(cur):
    layout = [[sg.Table(get_table(cur, 'tarefas', '*'), ['ID','Nome','Descrição', 'Tags'], num_rows=12)]]
    sg.Window('Ver tarefas', layout, icon=LOGO).read(close=True)

def ver_registros(cur):
    layout = [[sg.Table(get_table(cur, 'logs', 'id, dia, mes, ano, floor(duracao/60), tarefa'), 
                        ['ID', 'Dia','Mês','Ano', 'Duração(min)', 'Tarefa'], num_rows=12)]]
    sg.Window('Ver registros', layout, icon=LOGO).read(close=True)


def get_table(cur, name:str, items:str):
    cur.execute(f"SELECT {items} FROM {name}")
    return cur.fetchall()

def get_tarefas(cur):
    tarefas = get_table(cur, 'tarefas', 'nome')
    tarefas = [x[0] for x in tarefas]
    return tarefas

## event loop
def main():
    ## connect to database 
    con = sqlite3.connect('timer.db')
    ## create cursor
    cur = con.cursor()

    ## get tarefas
    tarefas = get_tarefas(cur)

    ## set theme
    sg.theme('BlueMono')

    ## create window
    layout = create_layout(tarefas)
    window = sg.Window('Timer', layout, icon=LOGO, finalize=True, resizable=True, enable_close_attempted_event=True)
    window.set_min_size((250,100))
    
    # window.bind('<FocusIn>', 'focus_in')
    # window.bind('<FocusOut>', 'focus_out')

    ## create tray icon
    tray = create_tray_icon(window)
    
    ## main loop
    is_counting = False

    dia : int = 0
    mes : int = 0
    ano : int = 0
    
    duracao : float = 0
    inicio : float = 0
    ultimo : float = time.time()
    tarefa : str = ''
    
    while True:
        event, values = window.read(timeout=100, timeout_key='refresh')

        if event in tray.key:
            event = values[event]

        match event:
            case 'Sair':
                break

            case 'Mostrar janela' | sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED:
                window.un_hide()
                window.bring_to_front()

            case 'Esconder Janela':
                window.hide()
                tray.show_icon()
            
            case sg.WIN_CLOSE_ATTEMPTED_EVENT:
                if not is_counting:
                    break
                window.hide()
                tray.show_icon()
            
            case 'refresh':
                if not is_counting:
                    continue

                duracao += time.time() - ultimo
                ultimo = time.time()

                window.Element('tempo').Update( str(timedelta(seconds=int(duracao)) ))

            case 'tarefa':
                tarefa = values['tarefa']
                window.Element('comecar').Update(disabled=False)

            case 'comecar':
                inicio = time.time()

                today = date.today()
                dia = int(today.strftime('%d'))
                mes = int(today.strftime('%m'))
                ano = int(today.strftime('%Y'))

                duracao = 0
                ultimo = time.time()
                is_counting = True

                window.refresh()
                time.sleep(0.1)

                window.Element('emoji').Update(EMOJI_RUNNING, text_color='green')
                window.Element('tarefa').Update(disabled=True)
                window.Element('comecar').Update(visible=False)
                window.Element('parar').Update(visible=True)
                window.Element('pausar').Update(visible=True)
                
            case 'pausar':
                ultimo = time.time()

                window.refresh()
                time.sleep(0.1)

                if is_counting:
                    window.Element('emoji').Update(EMOJI_PAUSE, text_color='red')
                    window.Element('pausar').Update("Continuar")
                else:
                    window.Element('emoji').Update(EMOJI_RUNNING, text_color='green')
                    window.Element('pausar').Update("Pausar")

                is_counting = not is_counting

            case 'parar':
                duracao += time.time() - ultimo
                is_counting = False

                cur.execute('INSERT INTO logs(dia, mes, ano, inicio, duracao, tarefa) VALUES(?, ?, ?, ?, ?, ?)', 
                                             (dia, mes, ano, inicio, duracao, tarefa))
                con.commit()

                window.refresh()
                time.sleep(0.1)

                window.Element('emoji').Update(EMOJI_PAUSE, text_color='red')
                window.Element('tempo').Update('0:00:00')
                window.Element('tarefa').Update(disabled=False)
                window.Element('parar').Update(visible=False)
                window.Element('pausar').Update("Pausar", visible=False)
                window.Element('comecar').Update(visible=True, disabled=True)
            
            case 'Ver tarefas':
                ver_tarefas(cur)

            case 'Adicionar tarefa':
                adicionar_tarefa(con, cur)
                tarefas = get_tarefas(cur)
                window.Element('tarefa').Update(values=tarefas)

            case 'Ver registros':
                ver_registros(cur)
                
    tray.close()
    window.close()
    exit(0)