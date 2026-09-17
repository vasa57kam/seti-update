import ast
p = 'static/gen.js'
js = open(p).read()
def rj(old, new, label):
    global js
    if old in js:
        js = js.replace(old, new, 1); print('  ok:', label)
    else:
        print('  ПРОПУСК:', label)

# 1) Шаблоны DDM
rj(" trunk:'config vlan vlanid {vlan} add tagged {ports}'\n}};",
   " trunk:'config vlan vlanid {vlan} add tagged {ports}',\n ddm:'show ddm ports {ports}',\n ddm_all:'show ddm'\n}};",
   'TPL: ddm')

# 2) Названия операций
rj("trunk:'КОМБО: магистраль на ядро (tagged)'};",
   "trunk:'КОМБО: магистраль на ядро (tagged)',ddm:'DDM оптики на порту (мощность/темп.)',ddm_all:'DDM всех портов (SFP)'};",
   'NAMES: ddm')

# 3) Подсказки
rj("trunk:'VLAN — номер VLAN, который пропускаем; Порт(ы) — магистральный порт на ядро/uplink.'};",
   "trunk:'VLAN — номер VLAN, который пропускаем; Порт(ы) — магистральный порт на ядро/uplink.',"
   "ddm:'Порт(ы) — порт с SFP-модулем (напр. 26 или 26-28). Покажет Tx/Rx мощность, температуру, напряжение — диагностика деградации оптики.',"
   "ddm_all:'Ничего вводить не надо — покажет DDM по всем портам, где стоят модули.'};",
   'HINTS: ddm')

# 4) Памятки
rj("port_info:'1) посмотреть состояние/скорость\\n2) порт down или не та скорость — проверить кабель и настройки'};",
   "port_info:'1) посмотреть состояние/скорость\\n2) порт down или не та скорость — проверить кабель и настройки',"
   "ddm:'1) посмотреть Tx/Rx мощность\\n2) Rx ниже -25 dBm или сильно хуже Tx — деградация оптики/грязный коннектор\\n3) почистить коннектор, заменить патч-корд или SFP\\n4) после замены — снова show ddm и сравнить',"
   "ddm_all:'1) найти порты с аномальной Rx мощностью\\n2) запланировать чистку/замену оптики'};",
   'MEMO: ddm')

open(p, 'w').write(js)
print('ok: gen.js + DDM')

src = open('swh.py').read()
if '/static/gen.js?v=7' not in src:
    src = src.replace('/static/gen.js?v=6', '/static/gen.js?v=7', 1)
    print('ok: версия gen.js -> v7')
open('swh.py', 'w').write(src)
ast.parse(open('swh.py').read())
print('update.py отработал, синтаксис ОК')