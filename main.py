from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from flask import send_file
import io
from datetime import datetime, timedelta
import os
import shutil
import pytz

app = Flask(__name__)

def hora_colombia():
    zona = pytz.timezone('America/Bogota')
    return datetime.now(zona).strftime('%Y-%m-%d %H:%M:%S')

def crear_db():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # TABLA USUARIOS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        usuario TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    # CREAR ADMIN SI NO EXISTE
    cursor.execute('''
    SELECT * FROM usuarios
    WHERE usuario = ?
    ''', ('admin',))

    admin = cursor.fetchone()

    if not admin:

        cursor.execute('''
        INSERT INTO usuarios (
            usuario,
            password
        )
        VALUES (?, ?)
        ''', (

            'admin',
            '1234'

        ))

    #Tabla Ingresos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingresos (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        placa TEXT NOT NULL,
        nombre TEXT NOT NULL,
        telefono TEXT NOT NULL,
        servicio TEXT NOT NULL,
        productos  TEXT,
        metodo_pago TEXT NOT NULL,
        total INTEGER NOT NULL,
        hora_entrada TEXT
    )
    ''')

    #Tabla Servicios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servicios (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        nombre TEXT NOT NULL,
        precio INTEGER NOT NULL
    )
    ''')

    # TABLA PRODUCTOS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        nombre TEXT NOT NULL,
        precio INTEGER NOT NULL,
        stock INTEGER NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historial (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        placa TEXT NOT NULL,
        nombre TEXT NOT NULL,
        telefono TEXT NOT NULL,
        servicio TEXT NOT NULL,
        productos TEXT,
        precio_lavado INTEGER NOT NULL,
        precio_producto INTEGER NOT NULL,
        total INTEGER NOT NULL,
        metodo_pago TEXT NOT NULL,
        hora_entrada TEXT,
        hora_salida TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cierres_mensuales (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        mes TEXT,
        total_ingresos INTEGER,
        total_motos INTEGER,
        servicio_top TEXT,

        fecha_cierre TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conexion.commit()
    conexion.close()


def crear_backup():

    try:

        # CARPETA ACTUAL DEL EXE
        ruta_base = os.getcwd()

        # DB
        db_path = os.path.join(
            ruta_base,
            'motolavado.db'
        )

        # CARPETA BACKUPS
        carpeta_backup = os.path.join(
            ruta_base,
            'backups'
        )

        # CREAR CARPETA
        if not os.path.exists(carpeta_backup):

            os.makedirs(carpeta_backup)

        # FECHA
        fecha = datetime.now().strftime('%Y-%m-%d')

        # ARCHIVO BACKUP
        backup_path = os.path.join(
            carpeta_backup,
            f'backup_{fecha}.db'
        )

        # CREAR BACKUP
        if os.path.exists(db_path):

            if not os.path.exists(backup_path):

                shutil.copy(
                    db_path,
                    backup_path
                )

                print("Backup creado")

        else:

            print("No existe la DB")

    except Exception as e:

        print("ERROR BACKUP:", e)

crear_db()

if os.path.exists('motolavado.db'):

    crear_backup()

# Página login
@app.route('/')
def inicio():
    return render_template('login.html')


# Validar login

@app.route('/login', methods=['POST'])
def login():

    usuario = request.form['name']

    password = request.form['password']

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    cursor.execute('''
    SELECT * FROM usuarios
    WHERE usuario = ?
    AND password = ?
    ''', (

        usuario,
        password

    ))

    usuario_db = cursor.fetchone()

    conexion.close()

    if usuario_db:

        return redirect(url_for('home'))

    else:

        return render_template(
            'login.html',
            message="Usuario o contraseña incorrectos"
        )

# Home principal
@app.route('/home')
def home():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    buscar = request.args.get('buscarPlaca')

    # SI BUSCA
    if buscar:

        cursor.execute('''
        SELECT * FROM ingresos
        WHERE placa LIKE ?
        ORDER BY id DESC
        ''', ('%' + buscar + '%',))

    else:

        cursor.execute('''
        SELECT * FROM ingresos
        ORDER BY id DESC
        ''')

    ingresos = cursor.fetchall()
    # PRODUCTOS
    cursor.execute('SELECT * FROM productos')

    productos = cursor.fetchall()

    conexion.close()

    return render_template(
        'home.html',
        ingresos=ingresos,
        productos=productos
    )
@app.route('/finalizar_servicio/<int:id>')
def finalizar_servicio(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # OBTENER INGRESO
    cursor.execute('''
    SELECT *
    FROM ingresos
    WHERE id = ?
    ''', (id,))

    ingreso = cursor.fetchone()

    # DATOS
    placa = ingreso[1]
    nombre = ingreso[2]
    telefono = ingreso[3]
    servicio = ingreso[4]
    productos = ingreso[5]
    metodo_pago = ingreso[6]
    total = ingreso[7]
    hora_entrada = ingreso[8]

    # BUSCAR PRECIO LAVADO
    cursor.execute('''
    SELECT precio
    FROM servicios
    WHERE nombre = ?
    ''', (servicio,))

    resultado = cursor.fetchone()

    if resultado:

        precio_lavado = resultado[0]

    else:

        precio_lavado = 0

    # PRECIO PRODUCTOS
    precio_producto = total - precio_lavado
    hora_salida = hora_colombia()

    cursor.execute('''
    INSERT INTO historial (

        placa,
        nombre,
        telefono,
        servicio,
        productos,
        precio_lavado,
        precio_producto,
        total,
        metodo_pago,
        hora_entrada,
        hora_salida

    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (

        ingreso[1],
        ingreso[2],
        ingreso[3],
        ingreso[4],
        ingreso[5],
        precio_lavado,
        precio_producto,
        ingreso[7],
        ingreso[6],
        ingreso[8],
        hora_salida

    ))

    # ELIMINAR DE HOME
    cursor.execute('''
    DELETE FROM ingresos
    WHERE id = ?
    ''', (id,))

    conexion.commit()

    conexion.close()

    return redirect(url_for('home'))

# Registrar moto
@app.route('/registrarmoto', methods=['GET', 'POST'])
def registrarmoto():

    conexion = sqlite3.connect('motolavado.db')
    cursor = conexion.cursor()

    # TRAER SERVICIOS
    cursor.execute('SELECT * FROM servicios')
    servicios = cursor.fetchall()

    # GUARDAR INGRESO
    if request.method == 'POST':

        placa = request.form['placa']
        nombre = request.form['name']
        telefono = request.form['telefono']
        servicio = request.form['servicio']
        metodo_pago = request.form['metododepago']

        # BUSCAR PRECIO DEL SERVICIO
        cursor.execute(
            'SELECT precio FROM servicios WHERE nombre = ?',
            (servicio,)
        )

        resultado = cursor.fetchone()

        if resultado:
            precio_servicio = resultado[0]
        else:
            precio_servicio = 0

        #HORA COLOMBIA (UTC-5 SIN LIBRERÍAS)
        hora_actual = hora_colombia()

        # INSERTAR INGRESO (AHORA CON HORA)
        cursor.execute('''
        INSERT INTO ingresos (
            placa,
            nombre,
            telefono,
            servicio,
            metodo_pago,
            total,
            hora_entrada
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            placa,
            nombre,
            telefono,
            servicio,
            metodo_pago,
            precio_servicio,
            hora_actual
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for('home'))

    conexion.close()

    return render_template(
        'registrarmoto.html',
        servicios=servicios
    )
# Historial
@app.route('/historial')
def historial():

    conexion = sqlite3.connect('motolavado.db')
    cursor = conexion.cursor()

    buscar = request.args.get('buscarPlaca')

    # PAGINACIÓN
    page = request.args.get('page', 1, type=int)
    por_pagina = 20
    offset = (page - 1) * por_pagina

    # CONDICIÓN DE BÚSQUEDA
    if buscar:
        cursor.execute('''
        SELECT COUNT(*) FROM historial
        WHERE placa LIKE ?
        ''', ('%' + buscar + '%',))
    else:
        cursor.execute('SELECT COUNT(*) FROM historial')

    total_registros = cursor.fetchone()[0]
    total_paginas = (total_registros + por_pagina - 1) // por_pagina

    # CONSULTA PAGINADA
    if buscar:
        cursor.execute('''
        SELECT * FROM historial
        WHERE placa LIKE ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        ''', ('%' + buscar + '%', por_pagina, offset))
    else:
        cursor.execute('''
        SELECT * FROM historial
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        ''', (por_pagina, offset))

    historial = cursor.fetchall()

    conexion.close()

    return render_template(
        'historial.html',
        historial=historial,
        page=page,
        total_paginas=total_paginas,
        buscar=buscar
    )
# Inventario
@app.route('/inventario', methods=['GET', 'POST'])
def inventario():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # GUARDAR PRODUCTO
    if request.method == 'POST':

        nombre = request.form['name']

        precio = request.form['precio']

        stock = request.form['stock']

        cursor.execute('''
        INSERT INTO productos (
            nombre,
            precio,
            stock
        )
        VALUES (?, ?, ?)
        ''', (
            nombre,
            precio,
            stock
        ))

        conexion.commit()

        return redirect(url_for('inventario'))

    # TABLA PRODUCTOS
    cursor.execute('SELECT * FROM productos')

    productos = cursor.fetchall()

    # REPORTE PRODUCTOS
    reporte_productos = []

    for producto in productos:

        nombre = producto[1]

        precio = producto[2]

        stock = producto[3]

        # BUSCAR CUÁNTO SE VENDIÓ
        cursor.execute('''
        SELECT productos FROM historial
        ''')

        historiales = cursor.fetchall()

        total_vendido = 0

        for historial in historiales:

            texto = historial[0]

            if texto and nombre in texto:

                partes = texto.split(',')

                for parte in partes:

                    if nombre in parte:

                        try:

                            cantidad = int(
                                parte.split('x')[1]
                            )

                            total_vendido += cantidad

                        except:

                            pass

        total_ingreso = total_vendido * precio

        reporte_productos.append((
            nombre,
            total_vendido,
            total_ingreso,
            stock
        ))

    conexion.close()

    return render_template(
        'inventario.html',
        productos=productos,
        reporte_productos=reporte_productos
    )
@app.route('/exportar_reporte_productos')
def exportar_reporte_productos():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    cursor.execute('''
    SELECT
        productos.nombre,
        COUNT(historial.id) as total_vendido,
        SUM(historial.precio_producto) as total_ingreso,
        productos.stock
    FROM productos

    LEFT JOIN historial
    ON historial.productos LIKE '%' || productos.nombre || '%'

    GROUP BY productos.nombre
    ''')

    reporte_productos = cursor.fetchall()

    conexion.close()

    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer
    )

    from reportlab.lib import colors

    from reportlab.lib.styles import getSampleStyleSheet

    from reportlab.lib.pagesizes import letter

    from flask import send_file

    pdf_path = 'reporte_productos.pdf'

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elementos = []

    titulo = Paragraph(
        "Reporte Productos",
        styles['Title']
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    data = [[
        'Nombre',
        'Total Vendido',
        'Total Ingreso',
        'Stock'
    ]]

    for reporte in reporte_productos:

        data.append([

            reporte[0],
            str(reporte[1]),
            f"${reporte[2] or 0}",
            str(reporte[3])

        ])

    tabla = Table(data)

    tabla.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('ALIGN', (0,0), (-1,-1), 'CENTER'),

        ('BOTTOMPADDING', (0,0), (-1,0), 12)

    ]))

    elementos.append(tabla)

    doc.build(elementos)

    return send_file(
        pdf_path,
        as_attachment=True
    )
@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    cursor.execute(
        'DELETE FROM productos WHERE id = ?',
        (id,)
    )

    conexion.commit()

    conexion.close()

    return redirect(url_for('inventario'))

@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # ACTUALIZAR
    if request.method == 'POST':

        nombre = request.form['name']

        precio = request.form['precio']

        stock = request.form['stock']

        cursor.execute('''
        UPDATE productos
        SET
            nombre = ?,
            precio = ?,
            stock = ?
        WHERE id = ?
        ''', (
            nombre,
            precio,
            stock,
            id
        ))

        conexion.commit()

        conexion.close()

        return redirect(url_for('inventario'))

    # TRAER PRODUCTO
    cursor.execute(
        'SELECT * FROM productos WHERE id = ?',
        (id,)
    )

    producto = cursor.fetchone()

    # TRAER TODOS
    cursor.execute('SELECT * FROM productos')

    productos = cursor.fetchall()

    conexion.close()

    return render_template(
        'inventario.html',
        producto_editar=producto,
        productos=productos
    )

# Reportes
# Reportes
@app.route('/reportes')
def reportes():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    zona = pytz.timezone('America/Bogota')

    ahora = datetime.now(zona)

    hoy = ahora.strftime('%Y-%m-%d')

    # INICIO DE SEMANA (LUNES)
    inicio_semana = ahora - timedelta(days=ahora.weekday())

    inicio_semana = inicio_semana.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # INICIO DE MES
    inicio_mes = ahora.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    hace_7_dias = (ahora - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    hace_30_dias = (ahora - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

    # ALERTA MES
    mes_actual = ahora.month

    cursor.execute('''
    SELECT fecha_cierre
    FROM cierres_mensuales
    ORDER BY id DESC
    LIMIT 1
    ''')

    ultimo_cierre = cursor.fetchone()

    mostrar_alerta = False

    if ultimo_cierre:

        fecha_cierre = ultimo_cierre[0]

        try:

            mes_cierre = datetime.strptime(
                fecha_cierre,
                "%Y-%m-%d %H:%M:%S"
            ).month

            if mes_cierre != mes_actual:

                mostrar_alerta = True

        except:

            mostrar_alerta = True

    else:

        mostrar_alerta = False

    filtro = request.args.get('filtro')

    condicion = ""
    parametros = ()

    # FILTRO HOY
    if filtro == 'hoy':

        condicion = """
        WHERE hora_salida LIKE ?
        """

        parametros = (f"{hoy}%",)

    # FILTRO SEMANA
    elif filtro == 'semana':

        fin_semana = inicio_semana + timedelta(days=6)

        condicion = """
        WHERE DATE(hora_salida)
        BETWEEN DATE(?) AND DATE(?)
        """

        parametros = (

            inicio_semana.strftime('%Y-%m-%d'),
            fin_semana.strftime('%Y-%m-%d')

        )

    # FILTRO MES
    elif filtro == 'mes':

        condicion = """
        WHERE strftime('%Y-%m', hora_salida) = ?
        """

        parametros = (
            ahora.strftime('%Y-%m'),
        )

    # TOTAL INGRESOS
    cursor.execute(f'''
    SELECT SUM(total)
    FROM historial
    {condicion}
    ''', parametros)

    total_ingresos = cursor.fetchone()[0]

    if total_ingresos is None:

        total_ingresos = 0

    # TOTAL MOTOS
    cursor.execute(f'''
    SELECT COUNT(*)
    FROM historial
    {condicion}
    ''', parametros)

    total_motos = cursor.fetchone()[0]

    # SERVICIO TOP
    cursor.execute(f'''
    SELECT servicio, COUNT(*) as cantidad
    FROM historial
    {condicion}
    GROUP BY servicio
    ORDER BY cantidad DESC
    ''', parametros)

    resultados = cursor.fetchall()

    if resultados:

        maximo = resultados[0][1]

        servicios_top = []

        for fila in resultados:

            if fila[1] == maximo:

                servicios_top.append(f"{fila[0]} ({fila[1]})")

        servicio_top = " - ".join(servicios_top)

    else:

        servicio_top = "Sin datos"

    conexion.close()

    return render_template(

        'reportes.html',

        total_ingresos=total_ingresos,
        total_motos=total_motos,
        servicio_top=servicio_top,

        mostrar_alerta=mostrar_alerta
    )
@app.route('/finalizar_mes')
def finalizar_mes():

    conexion = sqlite3.connect('motolavado.db')
    cursor = conexion.cursor()

    from datetime import datetime

    ahora = datetime.now()
    mes_actual_sql = ahora.strftime('%Y-%m')

    # 🔥 FILTRO DEL MES (BASE)
    condicion = "WHERE strftime('%Y-%m', hora_salida) = ?"
    params = (mes_actual_sql,)

    # TOTAL INGRESOS (SOLO MES)
    cursor.execute(f'''
    SELECT SUM(total)
    FROM historial
    {condicion}
    ''', params)

    total_ingresos = cursor.fetchone()[0] or 0

    # TOTAL MOTOS (SOLO MES)
    cursor.execute(f'''
    SELECT COUNT(*)
    FROM historial
    {condicion}
    ''', params)

    total_motos = cursor.fetchone()[0]

    # SERVICIO TOP (SOLO MES)
    cursor.execute(f'''
    SELECT servicio, COUNT(servicio) as cantidad
    FROM historial
    {condicion}
    GROUP BY servicio
    ORDER BY cantidad DESC
    LIMIT 1
    ''', params)

    resultado = cursor.fetchone()
    servicio_top = resultado[0] if resultado else "Sin datos"

    # MES TEXTO
    meses = [
        "Enero", "Febrero", "Marzo",
        "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre",
        "Octubre", "Noviembre", "Diciembre"
    ]

    mes_texto = f"{meses[ahora.month - 1]} {ahora.year}"

    # GUARDAR CIERRE
    cursor.execute('''
    INSERT INTO cierres_mensuales (
        mes,
        total_ingresos,
        total_motos,
        servicio_top
    )
    VALUES (?, ?, ?, ?)
    ''', (
        mes_texto,
        total_ingresos,
        total_motos,
        servicio_top
    ))

    # BORRAR SOLO MES ACTUAL
    cursor.execute('''
    DELETE FROM historial
    WHERE strftime('%Y-%m', hora_salida) = ?
    ''', (mes_actual_sql,))

    conexion.commit()
    conexion.close()

    return redirect(url_for('reportes'))
# Configuración
@app.route('/configuracion', methods=['GET', 'POST'])
def configuracion():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    mensaje = ""

    if request.method == 'POST':

        # CAMBIAR CONTRASEÑA
        if 'actual' in request.form:

            actual = request.form['actual']

            nueva = request.form['nueva']

            confirmar = request.form['confirmar']

            # VALIDAR CONTRASEÑA ACTUAL
            cursor.execute('''
            SELECT * FROM usuarios
            WHERE usuario = ?
            AND password = ?
            ''', (

                'admin',
                actual

            ))

            usuario_db = cursor.fetchone()

            if not usuario_db:

                mensaje = "Contraseña actual incorrecta"

            elif nueva != confirmar:

                mensaje = "Las contraseñas no coinciden"

            else:

                cursor.execute('''
                UPDATE usuarios
                SET password = ?
                WHERE usuario = ?
                ''', (

                    nueva,
                    'admin'

                ))

                conexion.commit()

                mensaje = "Contraseña actualizada correctamente"

        # GUARDAR SERVICIO
        else:

            nombre = request.form['servicio']

            precio = request.form['precio']

            cursor.execute('''
            INSERT INTO servicios (
                nombre,
                precio
            )
            VALUES (?, ?)
            ''', (

                nombre,
                precio

            ))

            conexion.commit()

            conexion.close()

            return redirect(url_for('configuracion'))

    # MOSTRAR SERVICIOS
    cursor.execute('SELECT * FROM servicios')

    servicios = cursor.fetchall()

    conexion.close()

    return render_template(
        'configuracion.html',
        servicios=servicios,
        mensaje=mensaje
    )
@app.route('/editar_ingreso/<int:id>', methods=['GET', 'POST'])
def editar_ingreso(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # TRAER SERVICIOS
    cursor.execute('SELECT * FROM servicios')

    servicios = cursor.fetchall()

    # ACTUALIZAR
    if request.method == 'POST':

        placa = request.form['placa']
        nombre = request.form['name']
        telefono = request.form['telefono']
        servicio = request.form['servicio']
        metodo_pago = request.form['metododepago']

        # BUSCAR PRECIO
        cursor.execute(
            'SELECT precio FROM servicios WHERE nombre = ?',
            (servicio,)
        )

        resultado = cursor.fetchone()

        if resultado:

            precio_servicio = resultado[0]

        else:

            precio_servicio = 0

        # UPDATE
        cursor.execute('''
        UPDATE ingresos
        SET
            placa = ?,
            nombre = ?,
            telefono = ?,
            servicio = ?,
            metodo_pago = ?,
            total = ?
        WHERE id = ?
        ''', (
            placa,
            nombre,
            telefono,
            servicio,
            metodo_pago,
            precio_servicio,
            id
        ))

        conexion.commit()

        conexion.close()

        return redirect(url_for('home'))

    # TRAER INGRESO
    cursor.execute(
        'SELECT * FROM ingresos WHERE id = ?',
        (id,)
    )

    ingreso = cursor.fetchone()

    conexion.close()

    return render_template(
        'registrarmoto.html',
        ingreso_editar=ingreso,
        servicios=servicios
    )

@app.route('/eliminar_servicio/<int:id>')
def eliminar_servicio(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    cursor.execute(
        'DELETE FROM servicios WHERE id = ?',
        (id,)
    )

    conexion.commit()

    conexion.close()

    return redirect(url_for('configuracion'))

@app.route('/editar_servicio/<int:id>', methods=['GET', 'POST'])
def editar_servicio(id):

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    # ACTUALIZAR
    if request.method == 'POST':

        nombre = request.form['servicio']
        precio = request.form['precio']

        cursor.execute('''
        UPDATE servicios
        SET nombre = ?, precio = ?
        WHERE id = ?
        ''', (nombre, precio, id))

        conexion.commit()

        conexion.close()

        return redirect(url_for('configuracion'))

    # OBTENER SERVICIO A EDITAR
    cursor.execute(
        'SELECT * FROM servicios WHERE id = ?',
        (id,)
    )

    servicio = cursor.fetchone()

    # OBTENER TODOS LOS SERVICIOS
    cursor.execute('SELECT * FROM servicios')

    servicios = cursor.fetchall()

    conexion.close()

    return render_template(
        'configuracion.html',
        servicio_editar=servicio,
        servicios=servicios
    )

@app.route('/guardar_productos', methods=['POST'])
def guardar_productos():

    data = request.get_json()

    productos = data['productos']

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    texto_productos = ""

    total_productos = 0

    # ULTIMO INGRESO
    cursor.execute('''
    SELECT id FROM ingresos
    ORDER BY id DESC LIMIT 1
    ''')

    ingreso_id = data['ingreso_id']

    # RECORRER PRODUCTOS
    for producto in productos:

        nombre = producto['nombre']

        precio = producto['precio']

        cantidad = producto['cantidad']

        subtotal = precio * cantidad

        total_productos += subtotal

        texto_productos += f"{nombre} x{cantidad}, "

        # RESTAR STOCK
        cursor.execute('''
        UPDATE productos
        SET stock = stock - ?
        WHERE nombre = ?
        ''', (
            cantidad,
            nombre
        ))

    # ACTUALIZAR INGRESO
    cursor.execute('''
    UPDATE ingresos
    SET
        productos = ?,
        total = total + ?
    WHERE id = ?
    ''', (
        texto_productos,
        total_productos,
        ingreso_id
    ))
    conexion.commit()

    conexion.close()

    return jsonify({
        'success': True
    })

@app.route('/exportar_reporte')
def exportar_reporte():

    conexion = sqlite3.connect('motolavado.db')

    cursor = conexion.cursor()

    cursor.execute('''
    SELECT
        placa,
        nombre,
        servicio,
        precio_lavado,
        precio_producto,
        total,
        metodo_pago
    FROM historial
    ''')

    datos = cursor.fetchall()

    conexion.close()

    # CREAR PDF EN MEMORIA
    buffer = io.BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter
    )

    elementos = []

    estilos = getSampleStyleSheet()

    titulo = Paragraph(
        "Reporte RiverMC",
        estilos['Title']
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    # TABLA
    tabla_datos = [[
        'Placa',
        'Dueño',
        'Servicio',
        'Lavado',
        'Productos',
        'Total',
        'Método'
    ]]

    for fila in datos:

        tabla_datos.append([
            fila[0],
            fila[1],
            fila[2],
            f"${fila[3]}",
            f"${fila[4]}",
            f"${fila[5]}",
            fila[6]
        ])

    tabla = Table(tabla_datos)

    tabla.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.black),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0,0), (-1,0), 10),

    ]))

    elementos.append(tabla)

    pdf.build(elementos)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='reporte_rivermc.pdf',
        mimetype='application/pdf'
    )

import webbrowser
from threading import Timer

def abrir_navegador():

    webbrowser.open(
        'http://127.0.0.1:5000'
    )

if __name__ == '__main__':

    Timer(1, abrir_navegador).start()

    app.run(debug=False)

