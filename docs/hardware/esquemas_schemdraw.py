import schemdraw
import schemdraw.elements as elm

schemdraw.config(fontsize=11, font='DejaVu Sans', lw=1.3)
NET = '#1f4e79'
FS = 10


def ic(pins, size, lbl, spacing=1.0):
    """pins: list of (nome, lado, anchor). Em cada lado, a ordem e de baixo para cima."""
    e = elm.Ic(pins=[elm.IcPin(name=n, side=s, anchorname=a) for n, s, a in pins],
               size=size, pinspacing=spacing, plblsize=10)
    return e.theta(0).anchor('center').label(lbl, loc='top', fontsize=11, ofst=0.25)


def netlabel(d, p, text, side):
    d += elm.Dot(open=True).at(p).label(text, loc=side, fontsize=FS, color=NET)


def stub_net(d, p, dx, text):
    ln = elm.Line().at(p).to((p[0] + dx, p[1]))
    d += ln
    netlabel(d, ln.end, text, 'right' if dx > 0 else 'left')


def pwr(d, p, dx, text):
    d += elm.Line().at(p).to((p[0] + dx, p[1]))
    d += elm.Vdd().at((p[0] + dx, p[1])).label(text, fontsize=FS)


def gnd(d, p, dx, text=None):
    d += elm.Line().at(p).to((p[0] + dx, p[1]))
    g = elm.Ground().at((p[0] + dx, p[1]))
    if text:
        g = g.label(text, loc='right', fontsize=FS)
    d += g


def note(d, p, text):
    d += elm.Label().at(p).label(text, fontsize=FS, color='#555555')


# ======================================================== MEDIDOR
with schemdraw.Drawing(file='esquema_medidor.png', dpi=170, show=False) as d:
    esp = ic([('GND', 'left', 'gnd'), ('3V3', 'left', 'v33'), ('VIN (5 V)', 'left', 'vin'),
              ('GPIO27', 'right', 'g19'), ('GPIO22 (SCL)', 'right', 'g22'), ('GPIO21 (SDA)', 'right', 'g21'),
              ('GPIO4', 'right', 'g4'), ('GPIO34', 'right', 'g18'), ('GPIO33', 'right', 'g23')],
             (5.2, 7.0), 'ESP32 DevKit V1 (rsv-medidor-01)', spacing=1.0)
    d += esp.at((0, 0))
    stub_net(d, esp.vin, -1.2, '+5V (USB)')
    stub_net(d, esp.v33, -1.2, '+3V3')
    gnd(d, esp.gnd, -1.0)
    stub_net(d, esp.g23, 1.4, 'TRIG')
    stub_net(d, esp.g18, 1.4, 'ECHO_3V3')
    stub_net(d, esp.g4, 1.4, 'DQ')
    stub_net(d, esp.g21, 1.4, 'SDA_3V3')
    stub_net(d, esp.g22, 1.4, 'SCL_3V3')
    stub_net(d, esp.g19, 1.4, 'BUZ')
    note(d, (0, -4.6), 'Alimentação: carregador USB 5 V / 1 A')

    # ---- HC-SR04 com divisor no ECHO
    hc = ic([('GND', 'left', 'gnd'), ('ECHO', 'left', 'echo'), ('TRIG', 'left', 'trig'), ('VCC', 'left', 'vcc')],
            (2.6, 5.0), 'HC-SR04', spacing=1.2)
    d += hc.at((19, 5.5))
    pwr(d, hc.vcc, -0.9, '+5V')
    stub_net(d, hc.trig, -5.2, 'TRIG')
    r1 = elm.Resistor().at(hc.echo).to((hc.echo[0] - 3.0, hc.echo[1])).label('R1  1 kΩ', fontsize=FS)
    d += r1
    d += elm.Dot().at(r1.end)
    stub_net(d, r1.end, -2.2, 'ECHO_3V3')
    d += elm.Resistor().at(r1.end).down(2.4).label('R2\n2 kΩ', loc='bottom', fontsize=FS)
    d += elm.Ground()
    gnd(d, hc.gnd, -0.9)
    note(d, (14.2, 9.2), 'Divisor do ECHO: 5 V x 2k/(1k+2k) = 3,33 V')

    # ---- DS18B20 com pull-up
    ds = ic([('GND', 'left', 'gnd'), ('DQ', 'left', 'dq'), ('VDD', 'left', 'vdd')],
            (2.6, 3.8), "DS18B20 (sonda)", spacing=1.2)
    d += ds.at((19, -1.5))
    pwr(d, ds.vdd, -0.9, '+3V3')
    ldq = elm.Line().at(ds.dq).to((ds.dq[0] - 2.4, ds.dq[1]))
    d += ldq
    d += elm.Dot().at(ldq.end)
    d += elm.Resistor().at(ldq.end).up(2.2).label('R3\n4,7 kΩ', loc='bottom', fontsize=FS)
    d += elm.Vdd().label('+3V3', fontsize=FS)
    stub_net(d, ldq.end, -2.8, 'DQ')
    gnd(d, ds.gnd, -0.9)

    # ---- Conversor de nível + LCD
    ls = ic([('GND', 'left', 'gnd'), ('LV2', 'left', 'lv2'), ('LV1', 'left', 'lv1'), ('LV', 'left', 'lv'),
             ('GND', 'right', 'gnd2'), ('HV2', 'right', 'hv2'), ('HV1', 'right', 'hv1'), ('HV', 'right', 'hv')],
            (3.0, 4.8), 'Conversor de nível BSS138', spacing=1.1)
    d += ls.at((12.5, -8.5))
    pwr(d, ls.lv, -0.9, '+3V3')
    stub_net(d, ls.lv1, -1.6, 'SDA_3V3')
    stub_net(d, ls.lv2, -1.6, 'SCL_3V3')
    gnd(d, ls.gnd, -0.9)
    lcd = ic([('GND', 'left', 'gnd'), ('SCL', 'left', 'scl'), ('SDA', 'left', 'sda'), ('VCC', 'left', 'vcc')],
             (3.0, 4.8), 'LCD 16x2 I2C (PCF8574)', spacing=1.1)
    d += lcd.at((21.0, -8.5))
    d += elm.Line().at(ls.hv1).to(lcd.sda)
    d += elm.Line().at(ls.hv2).to(lcd.scl)
    pwr(d, ls.hv, 0.9, '+5V')
    gnd(d, ls.gnd2, 0.9)
    pwr(d, lcd.vcc, -0.9, '+5V')
    gnd(d, lcd.gnd, -0.9)

    # ---- Buzzer com transistor
    bx, by = -1.5, -10.5
    netlabel(d, (bx, by), 'BUZ', 'left')
    rb = elm.Resistor().at((bx, by)).right(2.6).label('R4  1 kΩ', fontsize=FS)
    d += rb
    q = elm.BjtNpn(circle=True).anchor('base').at(rb.end).label('Q1 BC547', loc='right', fontsize=FS)
    d += q
    d += elm.Line().at(q.emitter).down(0.5)
    d += elm.Ground()
    lc = elm.Line().at(q.collector).up(0.5)
    d += lc
    d += elm.Dot()
    top = lc.end
    bz = elm.ResistorIEC().at(top).up(2.4).label('BZ1 buzzer\nativo 5 V', loc='bottom', fontsize=FS)
    d += bz
    d += elm.Dot().at(bz.end)
    d += elm.Line().at(bz.end).up(0.5)
    d += elm.Vdd().label('+5V', fontsize=FS)
    d += elm.Line().at(top).right(3.0)
    d += elm.Diode().up(2.4).reverse().label('D1 1N4148', loc='bottom', fontsize=FS)
    d += elm.Line().to(bz.end)

    note(d, (5, -16.0), 'Ligações por rótulo de rede: pontos com o mesmo nome (TRIG, ECHO_3V3, DQ, SDA_3V3, SCL_3V3, BUZ, +5V, +3V3) estão conectados. GND comum.')

# ======================================================== CONTROLADOR
with schemdraw.Drawing(file='esquema_controlador.png', dpi=170, show=False) as d:
    esp = ic([('GND', 'left', 'gnd'), ('VIN (5 V)', 'left', 'vin'),
              ('GPIO27', 'right', 'g27'), ('GPIO25', 'right', 'g25'), ('GPIO26', 'right', 'g26')],
             (4.6, 4.4), 'ESP32 DevKit V1 (rsv-controlador-01)', spacing=1.0)
    d += esp.at((0, 0))
    stub_net(d, esp.vin, -1.2, '+5V_A')
    gnd(d, esp.gnd, -1.0)
    stub_net(d, esp.g26, 1.4, 'RELE_IN')
    stub_net(d, esp.g25, 1.4, 'LED_VD')
    stub_net(d, esp.g27, 1.4, 'LED_VM')
    note(d, (0, -3.3), 'Fonte A: carregador USB 5 V / 1 A')

    for i, (n, r, lbl) in enumerate([('LED_VD', 'R6\n330 Ω', 'LD1 verde\n(operando)'),
                                      ('LED_VM', 'R7\n330 Ω', 'LD2 vermelho\n(MODO_SEGURO)')]):
        x, y = -1.8 + i * 4.6, -5.0
        netlabel(d, (x, y), n, 'top')
        d += elm.Resistor().at((x, y)).down(2.2).label(r, loc='bottom', fontsize=FS)
        d += elm.LED().down(2.2).label(lbl, loc='bottom', fontsize=FS)
        d += elm.Ground()

    rl = ic([('GND', 'left', 'gnd'), ('IN', 'left', 'inp'), ('VCC', 'left', 'vcc'),
             ('NC', 'right', 'nc'), ('NO', 'right', 'no'), ('COM', 'right', 'com')],
            (3.4, 4.0), 'Módulo relé 5 V (1 canal)', spacing=1.2)
    d += rl.at((15.5, 0))
    note(d, (15.5, -3.0), 'optoacoplado, trigger em nível ALTO')
    pwr(d, rl.vcc, -0.9, '+5V_A')
    li = elm.Line().at(rl.inp).to((rl.inp[0] - 2.6, rl.inp[1]))
    d += li
    d += elm.Dot().at(li.end)
    stub_net(d, li.end, -1.4, 'RELE_IN')
    d += elm.Resistor().at(li.end).down(3.0).label('R5\n10 kΩ', loc='bottom', fontsize=FS)
    d += elm.Ground()
    gnd(d, rl.gnd, -0.9)
    d += elm.Line().at(rl.nc).right(0.8)
    d += elm.Label().label('(livre)', loc='right', fontsize=FS)

    # circuito de potência (Fonte B)
    ytop, ybot = 4.5, -5.0
    xm, xd, xc1, xc2, xs = rl.no[0] + 3.0, rl.no[0] + 6.0, rl.no[0] + 8.5, rl.no[0] + 11.0, rl.no[0] + 13.5
    d += elm.Line().at(rl.com).right(0.8)
    d += elm.Line().up(ytop - rl.com[1])
    xf0 = rl.com[0] + 0.8
    d += elm.Fuse().at((xf0, ytop)).to((xf0 + 3.0, ytop)).label('F1  1 A', fontsize=FS)
    d += elm.Line().at((xf0 + 3.0, ytop)).to((xs, ytop))
    d += elm.Dot().at((xc2, ytop))
    d += elm.Capacitor(polar=True).at((xc2, ytop)).to((xc2, ybot)).label('C2\n470 µF\n16 V', loc='bottom', fontsize=FS)
    d += elm.SourceV().at((xs, ybot)).to((xs, ytop)).label('Fonte B\n5 V / 2 A', loc='bottom', fontsize=FS)

    ymt, ymb = rl.no[1] - 0.6, ybot + 1.2
    d += elm.Line().at(rl.no).to((xm, rl.no[1]))
    d += elm.Line().to((xm, ymt))
    d += elm.Dot()
    d += elm.Motor().at((xm, ymt)).to((xm, ymb)).label('M1 bomba\n5 V', loc='bottom', fontsize=FS)
    d += elm.Dot()
    d += elm.Line().at((xm, ymb)).to((xm, ybot))
    d += elm.Line().at((xm, ymt)).to((xd, ymt))
    d += elm.Diode().at((xd, ymt)).to((xd, ymb)).reverse().label('D2\n1N4007', loc='bottom', fontsize=FS)
    d += elm.Line().to((xm, ymb))
    d += elm.Line().at((xd, ymt)).to((xc1, ymt))
    d += elm.Capacitor().at((xc1, ymt)).to((xc1, ymb)).label('C1\n100 nF', loc='bottom', fontsize=FS)
    d += elm.Line().to((xd, ymb))
    d += elm.Line().at((xm, ybot)).to((xs, ybot))
    d += elm.Dot().at((xc2, ybot))
    gnd(d, (xs, ybot), 0.0, 'GND_B')
    note(d, ((xm + xs) / 2, ybot - 1.6), 'Fonte B alimenta só a bomba, através do contato COM/NO do relé (isolado da Fonte A)')
