from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import date, datetime, timedelta
from typing import List, Optional
import calendar
import os
import requests
import tempfile

from app.config import get_settings

settings = get_settings()

# Configurar nombres de meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

DIAS_SEMANA = {
    0: "L", 1: "M", 2: "M", 3: "J", 4: "V", 5: "S", 6: "D"
}

DIAS_SEMANA_NOMBRE = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
}


def descargar_imagen_firma(url: str) -> Optional[str]:
    """
    Descarga una imagen de firma desde URL y retorna el path temporal
    """
    if not url:
        return None
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Crear archivo temporal
            suffix = ".png" if "png" in url.lower() else ".jpg"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name
    except Exception as e:
        print(f"[ERROR] Descargando firma: {str(e)}")
    
    return None

# Colores corporativos
COLOR_HEADER = colors.Color(0.12, 0.23, 0.37)  # Azul oscuro IDS
COLOR_HEADER_TEXT = colors.white
COLOR_BORDER = colors.black
COLOR_LIGHT_GRAY = colors.Color(0.95, 0.95, 0.95)
COLOR_BOX_BORDER = colors.Color(0.7, 0.7, 0.7)


class RoundedBox(Flowable):
    """Crea un recuadro con esquinas redondeadas que contiene contenido"""
    
    def __init__(self, content, width, height=None, radius=8, stroke_color=COLOR_BOX_BORDER, stroke_width=1, fill_color=None, padding=10):
        Flowable.__init__(self)
        self.content = content
        self.box_width = width
        self.box_height = height
        self.radius = radius
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.padding = padding
        
    def wrap(self, availWidth, availHeight):
        # Calcular altura del contenido
        if self.box_height:
            return self.box_width, self.box_height
        
        # Estimar altura basada en el contenido
        if isinstance(self.content, Paragraph):
            w, h = self.content.wrap(self.box_width - 2*self.padding, availHeight)
            self.box_height = h + 2*self.padding
        else:
            self.box_height = 60  # Altura por defecto
            
        return self.box_width, self.box_height
    
    def draw(self):
        canvas = self.canv
        
        # Dibujar rectángulo redondeado
        if self.fill_color:
            canvas.setFillColor(self.fill_color)
            canvas.roundRect(0, 0, self.box_width, self.box_height, self.radius, stroke=0, fill=1)
        
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.stroke_width)
        canvas.roundRect(0, 0, self.box_width, self.box_height, self.radius, stroke=1, fill=0)
        
        # Dibujar contenido
        if isinstance(self.content, Paragraph):
            self.content.wrapOn(canvas, self.box_width - 2*self.padding, self.box_height)
            self.content.drawOn(canvas, self.padding, self.padding)


class SignatureBox(Flowable):
    """Crea un recuadro de firma con esquinas redondeadas"""
    
    def __init__(self, title, name, width=2.5*inch, height=1.2*inch, radius=8, firma_path=None):
        Flowable.__init__(self)
        self.title = title
        self.name = name
        self.box_width = width
        self.box_height = height
        self.radius = radius
        self.firma_path = firma_path
        
    def wrap(self, availWidth, availHeight):
        return self.box_width, self.box_height
    
    def draw(self):
        canvas = self.canv
        
        # Dibujar rectángulo redondeado
        canvas.setStrokeColor(COLOR_BOX_BORDER)
        canvas.setLineWidth(1)
        canvas.roundRect(0, 0, self.box_width, self.box_height, self.radius, stroke=1, fill=0)
        
        # Título arriba
        canvas.setFont('Helvetica', 9)
        title_width = canvas.stringWidth(self.title, 'Helvetica', 9)
        canvas.drawString((self.box_width - title_width) / 2, self.box_height - 18, self.title)
        
        # Si hay firma digital, mostrarla DENTRO del recuadro
        if self.firma_path and os.path.exists(self.firma_path):
            try:
                # Calcular posición centrada para la firma (encima de la línea, dentro del recuadro)
                firma_width = 1.0 * inch
                firma_height = 0.4 * inch
                x = (self.box_width - firma_width) / 2
                y = 40  # Posición encima de la línea pero dentro del recuadro
                canvas.drawImage(self.firma_path, x, y, width=firma_width, height=firma_height, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"[ERROR] Dibujando firma: {str(e)}")
        
        # Línea de firma (siempre se dibuja)
        line_y = 35
        line_margin = 20
        canvas.line(line_margin, line_y, self.box_width - line_margin, line_y)
        
        # Nombre abajo
        canvas.setFont('Helvetica-Bold', 9)
        name_width = canvas.stringWidth(self.name, 'Helvetica-Bold', 9)
        canvas.drawString((self.box_width - name_width) / 2, 15, self.name)


def generar_reporte_mensual(
    empleado: dict,
    actividades: List[dict],
    anio: int,
    mes: int,
    logo_path: Optional[str] = None,
    cliente: str = "Jugos del Valle S.A.P.I. de C.V.",
    proveedor: str = "Informática y Desarrollo en Sistemas S.A de C.V",
    proyecto: str = None
) -> BytesIO:
    """
    Genera un PDF con el reporte mensual de actividades
    Formato estilo IDS con logo y recuadro de información
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.4*inch,
        leftMargin=0.4*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    style_normal = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7, leading=9)
    style_title = ParagraphStyle('ReportTitle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    # Obtener nombre del mes y período
    mes_nombre = MESES_ES.get(mes, f"Mes {mes}")
    periodo_texto = f"{mes_nombre} {anio}"
    
    # ========================================
    # ENCABEZADO CON LOGO E INFO EN RECUADRO REDONDEADO
    # ========================================
    
    # Logo (lado izquierdo)
    logo_cell = ""
    default_logo_path = "app/static/img/logo.png"
    actual_logo_path = logo_path or default_logo_path
    
    if os.path.exists(actual_logo_path):
        try:
            logo_cell = Image(actual_logo_path, width=1.8*inch, height=0.7*inch)
        except:
            logo_cell = Paragraph("<b><font size='14'>ids.it</font></b><br/><font size='6'>INFORMÁTICA Y DESARROLLO EN SISTEMAS</font>", style_normal)
    else:
        logo_cell = Paragraph("<b><font size='14'>ids.it</font></b><br/><font size='6'>INFORMÁTICA Y DESARROLLO EN SISTEMAS</font>", style_normal)
    
    # Información del header (lado derecho en recuadro)
    proyecto_nombre = proyecto or empleado.get('proyecto', 'N/A')
    nombre_empleado = empleado.get('nombre_completo', '')
    # Usar cliente del empleado si está disponible
    cliente_empleado = empleado.get('cliente', cliente)
    
    info_text = f"""<font size='8'>
Cliente: {cliente_empleado}<br/>
Proveedor: {proveedor}<br/>
Proyecto: {proyecto_nombre}<br/>
Nombre: {nombre_empleado}<br/>
Período: {periodo_texto}
</font>"""
    
    info_paragraph = Paragraph(info_text, style_normal)
    
    # Recuadro con esquinas redondeadas
    info_box = RoundedBox(info_paragraph, width=4.5*inch, radius=10, padding=12)
    
    header_data = [[logo_cell, info_box]]
    header_table = Table(header_data, colWidths=[2.5*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ========================================
    # TABLA DE ACTIVIDADES CON TÍTULO INTEGRADO
    # ========================================
    
    num_dias = calendar.monthrange(anio, mes)[1]
    
    # Crear diccionario de actividades por fecha
    actividades_dict = {}
    for act in actividades:
        fecha_str = act.get('fecha')
        if fecha_str:
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.split('T')[0]).date()
            else:
                fecha = fecha_str
            actividades_dict[fecha.day] = act
    
    # Fila del título (será parte de la tabla)
    titulo_row = ['REPORTE MENSUAL DE ACTIVIDADES', '', '', '', '', '', '', '']
    
    # Encabezados de columnas
    headers_row = ['Fecha', 'Hora de\nEntrada', 'Hora Salida', 'Descripción de Actividades', 'Días', 'Horas\ntrabajadas', 'Días', 'HO- Officina']
    
    table_data = [titulo_row, headers_row]
    
    total_horas = 0
    total_dias = 0
    
    # Generar filas para cada día del mes
    for dia in range(1, num_dias + 1):
        fecha = date(anio, mes, dia)
        dia_semana = DIAS_SEMANA[fecha.weekday()]
        
        actividad = actividades_dict.get(dia, {})
        
        hora_entrada = actividad.get('hora_entrada', '')
        hora_salida = actividad.get('hora_salida', '')
        descripcion = actividad.get('descripcion', '')
        horas = float(actividad.get('horas_trabajadas', 0))
        
        # Obtener código de ubicación
        ubicacion_codigo = ''
        if actividad:
            ubicacion = actividad.get('ubicacion')
            if isinstance(ubicacion, dict):
                ubicacion_codigo = ubicacion.get('codigo', 'HO')
            elif actividad.get('ubicacion_id'):
                ubicacion_codigo = 'HO'
        
        # Formatear horas
        if hora_entrada:
            if isinstance(hora_entrada, str):
                hora_entrada = hora_entrada[:5]
            else:
                hora_entrada = hora_entrada.strftime('%H:%M') if hasattr(hora_entrada, 'strftime') else str(hora_entrada)[:5]
        
        if hora_salida:
            if isinstance(hora_salida, str):
                hora_salida = hora_salida[:5]
            else:
                hora_salida = hora_salida.strftime('%H:%M') if hasattr(hora_salida, 'strftime') else str(hora_salida)[:5]
        
        dia_trabajado = 1 if horas > 0 else 0
        
        if horas > 0:
            total_horas += horas
            total_dias += dia_trabajado
        
        horas_str = f"{int(horas):02d}:00" if horas > 0 else ''
        
        row = [
            str(dia),
            hora_entrada or '',
            hora_salida or '',
            descripcion or '',
            dia_semana,
            horas_str,
            str(dia_trabajado) if dia_trabajado else '',
            ubicacion_codigo if dia_trabajado else ''
        ]
        
        table_data.append(row)
    
    # Fila de totales
    table_data.append(['', '', '', 'Total de horas / días del mes', '', str(int(total_horas)), str(total_dias), ''])
    
    # Anchos de columna
    col_widths = [0.45*inch, 0.6*inch, 0.6*inch, 3.0*inch, 0.35*inch, 0.6*inch, 0.35*inch, 0.85*inch]
    
    main_table = Table(table_data, colWidths=col_widths, repeatRows=2)
    
    # Estilos de la tabla
    table_style = [
        # Fila del título
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_HEADER_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Encabezados de columnas
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_LIGHT_GRAY),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 7),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
        
        # Contenido
        ('FONTSIZE', (0, 2), (-1, -1), 7),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 2), (0, -1), 'CENTER'),
        ('ALIGN', (1, 2), (2, -1), 'CENTER'),
        ('ALIGN', (3, 2), (3, -1), 'LEFT'),
        ('ALIGN', (4, 2), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 2), (-1, -1), 'MIDDLE'),
        
        # Bordes
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        
        # Fila de totales
        ('FONTNAME', (3, -1), (6, -1), 'Helvetica-Bold'),
    ]
    
    # Resaltar fines de semana
    for i, dia in enumerate(range(1, num_dias + 1), start=2):
        fecha = date(anio, mes, dia)
        if fecha.weekday() >= 5:
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))
    
    main_table.setStyle(TableStyle(table_style))
    elements.append(main_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========================================
    # OBSERVACIONES CON ESQUINAS REDONDEADAS
    # ========================================
    elements.append(Paragraph("<b>Observaciones</b>", style_normal))
    elements.append(Spacer(1, 0.05*inch))
    
    # Recuadro de observaciones redondeado
    obs_box = RoundedBox(Paragraph("", style_normal), width=7.3*inch, height=0.4*inch, radius=8)
    elements.append(obs_box)
    elements.append(Spacer(1, 0.1*inch))
    
    # ========================================
    # TEXTO DE ACEPTACIÓN Y FIRMAS CON RECUADROS REDONDEADOS
    # ========================================
    acepto_text = """Acepto que las actividades descritas en este reporte fueron hechas a mi satisfacción y acepto los cargos que por concepto de las mismas Informática y Desarrollo en Sistemas, S. A. De C. V. Facturará a mi empresa."""
    elements.append(Paragraph(acepto_text, style_small))
    elements.append(Spacer(1, 0.35*inch))
    
    # Obtener firma digital si existe
    firma_url = empleado.get('firma_url')
    firma_temp_path = None
    if firma_url:
        firma_temp_path = descargar_imagen_firma(firma_url)
    
    # Crear recuadros de firma con esquinas redondeadas
    firma_consultor = SignatureBox("Consultor", nombre_empleado, width=2.8*inch, height=1.1*inch, radius=10, firma_path=firma_temp_path)
    firma_empresa = SignatureBox("Informática y Desarrollo en Sistemas", "IDS", width=2.8*inch, height=1.1*inch, radius=10)
    
    firma_data = [[firma_consultor, '', firma_empresa]]
    firma_table = Table(firma_data, colWidths=[2.8*inch, 1.7*inch, 2.8*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(firma_table)
    
    # Número de página
    elements.append(Spacer(1, 0.15*inch))
    elements.append(Paragraph("<font size='7'>1</font>", ParagraphStyle('PageNum', alignment=TA_RIGHT)))
    
    doc.build(elements)
    
    # Limpiar archivo temporal de firma
    if firma_temp_path and os.path.exists(firma_temp_path):
        try:
            os.unlink(firma_temp_path)
        except:
            pass
    
    buffer.seek(0)
    return buffer


def generar_reporte_semanal(
    empleado: dict,
    actividades: List[dict],
    semana_inicio: date,
    logo_path: Optional[str] = None,
    cliente: str = "Jugos del Valle S.A.P.I. de C.V.",
    proveedor: str = "Informática y Desarrollo en Sistemas S.A de C.V",
    proyecto: str = None
) -> BytesIO:
    """
    Genera un PDF con el reporte semanal de actividades
    Formato estilo IDS con logo, recuadro y 7 días (incluyendo fin de semana)
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.4*inch,
        leftMargin=0.4*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    style_normal = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7, leading=9)
    
    # Calcular período (mes del inicio de semana)
    mes_nombre = MESES_ES.get(semana_inicio.month, f"Mes {semana_inicio.month}")
    periodo_texto = f"{mes_nombre} {semana_inicio.year}"
    
    # ========================================
    # ENCABEZADO CON LOGO E INFO EN RECUADRO REDONDEADO
    # ========================================
    
    # Logo
    logo_cell = ""
    default_logo_path = "app/static/img/logo.png"
    actual_logo_path = logo_path or default_logo_path
    
    if os.path.exists(actual_logo_path):
        try:
            logo_cell = Image(actual_logo_path, width=1.8*inch, height=0.7*inch)
        except:
            logo_cell = Paragraph("<b><font size='14'>ids.it</font></b><br/><font size='6'>INFORMÁTICA Y DESARROLLO EN SISTEMAS</font>", style_normal)
    else:
        logo_cell = Paragraph("<b><font size='14'>ids.it</font></b><br/><font size='6'>INFORMÁTICA Y DESARROLLO EN SISTEMAS</font>", style_normal)
    
    # Información del header
    proyecto_nombre = proyecto or empleado.get('proyecto', 'N/A')
    nombre_empleado = empleado.get('nombre_completo', '')
    supervisor = empleado.get('supervisor', 'N/A')
    # Usar cliente del empleado si está disponible
    cliente_empleado = empleado.get('cliente', cliente)
    
    info_text = f"""<font size='8'>
Cliente: {cliente_empleado}<br/>
Proveedor: {proveedor}<br/>
Proyecto: {proyecto_nombre}<br/>
Nombre: {nombre_empleado}<br/>
Período: {periodo_texto}
</font>"""
    
    info_paragraph = Paragraph(info_text, style_normal)
    
    # Recuadro con esquinas redondeadas
    info_box = RoundedBox(info_paragraph, width=4.5*inch, radius=10, padding=12)
    
    header_data = [[logo_cell, info_box]]
    header_table = Table(header_data, colWidths=[2.5*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ========================================
    # TABLA CON TÍTULO INTEGRADO - 7 DÍAS
    # ========================================
    
    semana_fin = semana_inicio + timedelta(days=6)  # Incluir domingo
    
    # Título como primera fila
    titulo_text = f"REPORTE SEMANAL DE ACTIVIDADES"
    subtitulo_text = f"Semana del {semana_inicio.strftime('%d/%m/%Y')} al {semana_fin.strftime('%d/%m/%Y')}"
    
    # Fila de título
    titulo_row = [f"{titulo_text}\n{subtitulo_text}", '', '', '', '', '', '']
    
    # Encabezados - Fecha antes de Día
    headers_row = ['Fecha', 'Día', 'Entrada', 'Salida', 'Horas', 'Descripción', 'Ubicación']
    
    table_data = [titulo_row, headers_row]
    
    # Crear diccionario de actividades
    actividades_dict = {}
    for act in actividades:
        fecha_str = act.get('fecha')
        if fecha_str:
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.split('T')[0]).date()
            else:
                fecha = fecha_str
            actividades_dict[fecha] = act
    
    total_horas = 0
    
    # 7 días (Lunes a Domingo)
    for i in range(7):
        fecha = semana_inicio + timedelta(days=i)
        dia_nombre = DIAS_SEMANA_NOMBRE[fecha.weekday()]
        actividad = actividades_dict.get(fecha, {})
        
        horas = float(actividad.get('horas_trabajadas', 0))
        total_horas += horas
        
        # Obtener ubicación
        ubicacion_nombre = ''
        if actividad:
            ubicacion = actividad.get('ubicacion')
            if isinstance(ubicacion, dict):
                ubicacion_nombre = ubicacion.get('nombre', ubicacion.get('codigo', ''))
            elif actividad.get('ubicacion_id'):
                ubicacion_nombre = 'Oficina'
        
        hora_entrada = actividad.get('hora_entrada', '')
        hora_salida = actividad.get('hora_salida', '')
        
        if hora_entrada and isinstance(hora_entrada, str):
            hora_entrada = hora_entrada[:5]
        if hora_salida and isinstance(hora_salida, str):
            hora_salida = hora_salida[:5]
        
        row = [
            fecha.strftime('%d/%m'),
            dia_nombre,
            hora_entrada or '',
            hora_salida or '',
            f"{horas:.1f}" if horas > 0 else '',
            actividad.get('descripcion', ''),
            ubicacion_nombre
        ]
        table_data.append(row)
    
    # Fila de total
    table_data.append(['', '', '', 'Total:', f"{total_horas:.1f}", '', ''])
    
    col_widths = [0.6*inch, 0.85*inch, 0.6*inch, 0.6*inch, 0.5*inch, 2.8*inch, 0.85*inch]
    
    main_table = Table(table_data, colWidths=col_widths, repeatRows=2)
    
    table_style = [
        # Fila del título
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_HEADER_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Encabezados
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_HEADER),
        ('TEXTCOLOR', (0, 1), (-1, 1), COLOR_HEADER_TEXT),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
        
        # Contenido
        ('FONTSIZE', (0, 2), (-1, -1), 8),
        ('ALIGN', (0, 2), (4, -1), 'CENTER'),
        ('ALIGN', (5, 2), (5, -1), 'LEFT'),
        ('ALIGN', (6, 2), (6, -1), 'CENTER'),
        ('VALIGN', (0, 2), (-1, -1), 'MIDDLE'),
        
        # Bordes
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        
        # Fila de totales
        ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT_GRAY),
    ]
    
    # Resaltar fines de semana (filas 7 y 8 = Sábado y Domingo, índice 7 y 8 considerando título y headers)
    table_style.append(('BACKGROUND', (0, 7), (-1, 7), colors.Color(0.95, 0.95, 0.95)))  # Sábado
    table_style.append(('BACKGROUND', (0, 8), (-1, 8), colors.Color(0.95, 0.95, 0.95)))  # Domingo
    
    main_table.setStyle(TableStyle(table_style))
    elements.append(main_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # ========================================
    # FIRMAS CON RECUADROS REDONDEADOS
    # ========================================
    # Obtener firma digital si existe
    firma_url = empleado.get('firma_url')
    firma_temp_path = None
    if firma_url:
        firma_temp_path = descargar_imagen_firma(firma_url)
    
    firma_empleado = SignatureBox("Consultor", nombre_empleado, width=2.8*inch, height=1.1*inch, radius=10, firma_path=firma_temp_path)
    firma_supervisor = SignatureBox("Supervisor", "Autorización", width=2.8*inch, height=1.1*inch, radius=10)
    
    firma_data = [[firma_empleado, '', firma_supervisor]]
    firma_table = Table(firma_data, colWidths=[2.8*inch, 1.7*inch, 2.8*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(firma_table)
    
    doc.build(elements)
    
    # Limpiar archivo temporal de firma
    if firma_temp_path and os.path.exists(firma_temp_path):
        try:
            os.unlink(firma_temp_path)
        except:
            pass
    
    buffer.seek(0)
    return buffer


def generar_formato_vacaciones(
    empleado: dict,
    vacacion: dict,
    logo_path: Optional[str] = None
) -> BytesIO:
    """
    Genera un PDF con el formato de solicitud de vacaciones
    Similar al formato Excel de IDS
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.4*inch,
        bottomMargin=0.4*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    style_title = ParagraphStyle('VacTitle', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER)
    style_normal = ParagraphStyle('VacNormal', parent=styles['Normal'], fontSize=9, leading=11)
    style_bold = ParagraphStyle('VacBold', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=11)
    style_small = ParagraphStyle('VacSmall', parent=styles['Normal'], fontSize=8, leading=10)
    style_center = ParagraphStyle('VacCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    
    # Colores
    color_header = colors.Color(0.12, 0.23, 0.37)  # Azul oscuro IDS
    color_light_blue = colors.Color(0.85, 0.92, 0.97)
    color_border = colors.Color(0.7, 0.7, 0.7)
    
    # ========================================
    # ENCABEZADO CON LOGO
    # ========================================
    logo_cell = ""
    default_logo_path = "app/static/img/logo.png"
    actual_logo_path = logo_path or default_logo_path
    
    if os.path.exists(actual_logo_path):
        try:
            logo_cell = Image(actual_logo_path, width=1.5*inch, height=0.6*inch)
        except:
            logo_cell = Paragraph("<b><font size='12' color='#1e3a5f'>ids.it</font></b>", style_normal)
    else:
        logo_cell = Paragraph("<b><font size='12' color='#1e3a5f'>ids.it</font></b>", style_normal)
    
    # Título
    title_cell = Paragraph("<b>SOLICITUD DE VACACIONES</b>", style_title)
    
    # Fecha de solicitud
    fecha_solicitud = vacacion.get('created_at', '')
    if isinstance(fecha_solicitud, str) and 'T' in fecha_solicitud:
        fecha_solicitud = fecha_solicitud.split('T')[0]
    fecha_cell = Paragraph(f"<b>FECHA:</b> {fecha_solicitud}", style_normal)
    
    header_data = [[logo_cell, title_cell, fecha_cell]]
    header_table = Table(header_data, colWidths=[1.8*inch, 4*inch, 1.7*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========================================
    # DATOS DEL EMPLEADO
    # ========================================
    nombre_completo = empleado.get('nombre_completo', f"{empleado.get('nombre', '')} {empleado.get('apellidos', '')}")
    numero_empleado = empleado.get('numero_empleado', 'N/A')
    puesto = empleado.get('puesto', 'N/A')
    fecha_ingreso = empleado.get('fecha_ingreso', 'N/A')
    
    # Calcular periodo trabajado (fecha_ingreso + 1 año)
    periodo_inicio = fecha_ingreso
    periodo_fin = ''
    if fecha_ingreso and fecha_ingreso != 'N/A':
        try:
            if isinstance(fecha_ingreso, str):
                fi = datetime.fromisoformat(fecha_ingreso.split('T')[0])
            else:
                fi = fecha_ingreso
            periodo_fin = (fi + timedelta(days=365)).strftime('%Y-%m-%d')
        except:
            periodo_fin = 'N/A'
    
    empleado_data = [
        [Paragraph("<b>NOMBRE:</b>", style_bold), Paragraph(nombre_completo, style_normal), 
         Paragraph("<b>N. EMPLEADO:</b>", style_bold), Paragraph(str(numero_empleado) if numero_empleado else 'N/A', style_normal)],
        [Paragraph("<b>PUESTO:</b>", style_bold), Paragraph(puesto, style_normal), '', ''],
        [Paragraph("<b>FECHA DE INGRESO:</b>", style_bold), Paragraph(str(fecha_ingreso), style_normal),
         Paragraph("<b>PERIODO TRABAJADO:</b>", style_bold), Paragraph(f"{periodo_inicio} AL {periodo_fin}", style_small)],
    ]
    
    empleado_table = Table(empleado_data, colWidths=[1.3*inch, 2.7*inch, 1.5*inch, 2*inch])
    empleado_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, color_border),
        ('BACKGROUND', (0, 0), (0, -1), color_light_blue),
        ('BACKGROUND', (2, 0), (2, -1), color_light_blue),
    ]))
    elements.append(empleado_table)
    elements.append(Spacer(1, 0.12*inch))
    
    # ========================================
    # DÍAS DE VACACIONES
    # ========================================
    dias_disponibles = float(empleado.get('dias_vacaciones', 0))
    dias_solicitados = float(vacacion.get('dias_solicitados', 0))
    dias_restantes = dias_disponibles - dias_solicitados
    
    dias_data = [
        [Paragraph("<b>DÍAS POR DISFRUTAR</b>", style_bold), 
         Paragraph(str(int(dias_disponibles)), style_center),
         Paragraph("<b>DÍAS SOLICITADOS</b>", style_bold), 
         Paragraph(str(int(dias_solicitados)), style_center),
         Paragraph("<b>RESTAN</b>", style_bold), 
         Paragraph(str(int(dias_restantes)), style_center)],
    ]
    
    dias_table = Table(dias_data, colWidths=[1.5*inch, 0.8*inch, 1.4*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    dias_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (3, 0), (3, 0), 'CENTER'),
        ('ALIGN', (5, 0), (5, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, color_border),
        ('BACKGROUND', (0, 0), (0, 0), color_light_blue),
        ('BACKGROUND', (2, 0), (2, 0), color_light_blue),
        ('BACKGROUND', (4, 0), (4, 0), color_light_blue),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTNAME', (5, 0), (5, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('FONTSIZE', (3, 0), (3, 0), 12),
        ('FONTSIZE', (5, 0), (5, 0), 12),
    ]))
    elements.append(dias_table)
    elements.append(Spacer(1, 0.12*inch))
    
    # ========================================
    # FECHAS POR TOMAR
    # ========================================
    elements.append(Paragraph("<b>FECHAS POR TOMAR:</b>", style_bold))
    elements.append(Spacer(1, 0.05*inch))
    
    dias_especificos = vacacion.get('dias_especificos', [])
    fecha_inicio = vacacion.get('fecha_inicio', '')
    fecha_fin = vacacion.get('fecha_fin', '')
    
    if dias_especificos and len(dias_especificos) > 0:
        # Mostrar días específicos
        fechas_formateadas = []
        for fecha in dias_especificos:
            try:
                if isinstance(fecha, str):
                    f = datetime.fromisoformat(fecha.split('T')[0])
                    fechas_formateadas.append(f.strftime('%d/%m/%Y'))
                else:
                    fechas_formateadas.append(str(fecha))
            except:
                fechas_formateadas.append(str(fecha))
        
        # Crear filas de fechas (máximo 4 por fila)
        fechas_rows = []
        for i in range(0, len(fechas_formateadas), 4):
            row = fechas_formateadas[i:i+4]
            while len(row) < 4:
                row.append('')
            fechas_rows.append(row)
        
        if fechas_rows:
            fechas_table = Table(fechas_rows, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
            fechas_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, color_border),
            ]))
            elements.append(fechas_table)
    else:
        # Mostrar rango de fechas
        rango_text = f"DEL {fecha_inicio} AL {fecha_fin}"
        elements.append(Paragraph(rango_text, style_center))
    
    elements.append(Spacer(1, 0.12*inch))
    
    # ========================================
    # TIPO DE SOLICITUD
    # ========================================
    elements.append(Paragraph("<b>TIPO DE SOLICITUD:</b>", style_bold))
    elements.append(Spacer(1, 0.05*inch))
    
    tipo_solicitud = vacacion.get('tipo_solicitud', 'usar_dias')
    
    # Crear checkboxes
    check_usar = "☑" if tipo_solicitud == 'usar_dias' else "☐"
    check_prima = "☑" if tipo_solicitud == 'prima_vacacional' else "☐"
    check_paternidad = "☑" if tipo_solicitud == 'paternidad' else "☐"
    
    tipo_data = [
        [f"{check_usar}  USAR DÍAS", f"{check_prima}  PAGO PRIMA VACACIONAL", f"{check_paternidad}  DÍAS POR PATERNIDAD"],
    ]
    
    tipo_table = Table(tipo_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
    tipo_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 0.5, color_border),
    ]))
    elements.append(tipo_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # ========================================
    # FIRMAS (con firma digital si existe)
    # ========================================
    firma_url = empleado.get('firma_url')
    firma_empleado_cell = '_' * 30  # Default sin firma
    
    if firma_url:
        try:
            # Descargar imagen directamente a memoria
            response = requests.get(firma_url, timeout=10)
            if response.status_code == 200:
                from io import BytesIO as FirmaBuffer
                firma_bytes = FirmaBuffer(response.content)
                firma_imagen = Image(firma_bytes, width=1.2*inch, height=0.5*inch)
                firma_empleado_cell = firma_imagen
        except Exception as e:
            print(f"[ERROR] Cargando firma en vacaciones: {e}")
            firma_empleado_cell = '_' * 30
    
    firma_data = [
        [firma_empleado_cell, '', '_' * 30],
        ['SOLICITA', '', 'AUTORIZA'],
        [nombre_completo, '', 'Recursos Humanos'],
    ]
    
    firma_table = Table(firma_data, colWidths=[3*inch, 1.5*inch, 3*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
    ]))
    elements.append(firma_table)
    
    elements.append(Spacer(1, 0.2*inch))
    
    # ========================================
    # ENCABEZADO OBSERVACIONES
    # ========================================
    elements.append(Paragraph("_" * 60, ParagraphStyle('Line', alignment=TA_CENTER)))
    elements.append(Paragraph("<b>INFORMÁTICA Y DESARROLLO EN<br/>SISTEMAS S. A. DE C.V.</b>", 
                              ParagraphStyle('CompanyName', fontSize=10, alignment=TA_CENTER, leading=12)))
    elements.append(Spacer(1, 0.1*inch))
    
    # ========================================
    # RECUADRO DE OBSERVACIONES
    # ========================================
    observaciones_text = """<b>OBSERVACIONES</b><br/><br/>
Si no se toman las vacaciones en el periodo correspondiente, se pierden los días.<br/><br/>
Los días de vacaciones no son acumulables.<br/><br/>
Las vacaciones tienen una vigencia de 12 meses posteriores a la fecha en que cumples años con la empresa. Es decir, si yo cumplo años con la empresa el 10 de enero del presente, tengo hasta el 10 de enero del siguiente año; para tomar mis vacaciones; de otra manera se pierden los días. Es importante planear sus días de descanso, desde el principio de tu nuevo periodo.<br/><br/>
Solicita tus vacaciones y prográmalas con un mes de anticipación."""
    
    obs_paragraph = Paragraph(observaciones_text, ParagraphStyle('Obs', fontSize=8, leading=11, alignment=TA_LEFT))
    
    obs_data = [[obs_paragraph]]
    obs_table = Table(obs_data, colWidths=[7*inch])
    obs_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(obs_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # ========================================
    # PIE DE PÁGINA CON DIRECCIÓN
    # ========================================
    elements.append(Paragraph("_" * 85, ParagraphStyle('FooterLine', alignment=TA_CENTER, fontSize=8)))
    elements.append(Paragraph(
        "<font size='7'>Daniel Huacuja #32, Magisterial Vista Bella, Tlanepantla, Estado de México. C. P. 54050 Tels.: 555359-4488 y 551663-0359</font>",
        ParagraphStyle('FooterAddress', alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer


def generar_responsiva_equipo(
    empleado: dict,
    equipo: dict,
    datos_responsiva: dict,
    nombre_entrega: str = "Nelson Rios Rengifo"
) -> BytesIO:
    """
    Genera el PDF de responsiva de equipo de cómputo.
    
    Args:
        empleado: Datos del empleado (nombre, apellidos, rfc, numero_empleado, puesto, cliente)
        equipo: Datos del equipo (modelo, marca, numero_serie, tipo, ubicacion)
        datos_responsiva: Datos adicionales (descripcion_equipo, procesador, pantalla, memoria_ram, 
                         disco_duro, dvd_rw, sistema_operativo)
        nombre_entrega: Nombre de quien entrega el equipo
    """
    buffer = BytesIO()
    
    # Configurar página carta
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    style_title = ParagraphStyle(
        'TitleResponsiva',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        spaceAfter=6,
        letterSpacing=4
    )
    
    style_company = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT
    )
    
    style_normal = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        leading=14
    )
    
    style_small = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.gray
    )
    
    style_bold = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold'
    )
    
    style_center = ParagraphStyle(
        'CenterText',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        alignment=TA_CENTER
    )
    
    style_underline = ParagraphStyle(
        'UnderlineText',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        underline=True
    )
    
    # Datos del empleado
    nombre_completo = f"{empleado.get('nombre', '')} {empleado.get('apellidos', '')}".strip()
    rfc = empleado.get('rfc', '') or ''
    numero_empleado = empleado.get('numero_empleado', '') or ''
    puesto = empleado.get('puesto', '') or ''
    cliente = empleado.get('cliente', '') or 'Jugos del Valle'
    proyecto = empleado.get('proyecto', '') or ''
    
    # Datos del equipo
    modelo = equipo.get('modelo', '') or ''
    marca = equipo.get('marca', '') or ''
    numero_serie = equipo.get('numero_serie', '') or ''
    tipo_equipo = equipo.get('tipo', 'laptop').capitalize()
    ubicacion = equipo.get('ubicacion', '') or ''
    
    # Datos de responsiva (capturados por admin)
    descripcion = datos_responsiva.get('descripcion_equipo', 'Prestamo')
    procesador = datos_responsiva.get('procesador', '')
    pantalla = datos_responsiva.get('pantalla', '')
    memoria_ram = datos_responsiva.get('memoria_ram', '')
    disco_duro = datos_responsiva.get('disco_duro', '')
    dvd_rw = datos_responsiva.get('dvd_rw', 'NO')
    sistema_operativo = datos_responsiva.get('sistema_operativo', '')
    
    # Fecha actual
    hoy = date.today()
    fecha_str = f"{hoy.day:02d} {MESES_ES[hoy.month]} de {hoy.year}"
    
    # ========================================
    # ENCABEZADO
    # ========================================
    # Logo y título en una tabla
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'logo_ids.png')
    
    header_data = [
        [
            Paragraph("R E S G U A R D O", style_title),
            ''
        ],
        [
            '',
            Paragraph("<b>INFORMÁTICA Y DESARROLLO EN SISTEMAS, S.A. DE C.V</b>", style_company)
        ]
    ]
    
    # Intentar agregar logo
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.5*inch, height=0.5*inch)
            header_data[0][1] = logo
            header_data[1][1] = Paragraph("<b>INFORMÁTICA Y DESARROLLO EN SISTEMAS, S.A. DE C.V</b>", style_company)
    except:
        pass
    
    header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # ========================================
    # FECHA
    # ========================================
    elements.append(Paragraph(f"<para align='right'>{fecha_str}</para>", style_normal))
    elements.append(Spacer(1, 0.2*inch))
    
    # ========================================
    # DATOS DEL EMPLEADO
    # ========================================
    # El que suscribe
    elements.append(Paragraph(
        f"El que suscribe: <u><b>{nombre_completo}</b></u>",
        style_normal
    ))
    elements.append(Paragraph("<font size='7' color='gray'>(Nombre)</font>", 
                             ParagraphStyle('SmallCenter', alignment=TA_CENTER, fontSize=7, textColor=colors.gray)))
    elements.append(Spacer(1, 0.1*inch))
    
    # RFC y No. Empleado en una línea
    elements.append(Paragraph(
        f"con R.F.C. <u><b>{rfc}</b></u>   No. De Empleado <u><b>{numero_empleado}</b></u>",
        style_normal
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    # Puesto y Proyecto
    puesto_proyecto_data = [
        [
            Paragraph(f"Puesto de: <u><b>{puesto}</b></u>", style_normal),
            Paragraph(f"Proyecto <u><b>{proyecto}</b></u>", style_normal)
        ],
        [
            Paragraph("<font size='7' color='gray'>(Indicar puesto y Nombramiento)</font>", style_small),
            ''
        ]
    ]
    puesto_table = Table(puesto_proyecto_data, colWidths=[4*inch, 3*inch])
    puesto_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(puesto_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Adscrito a
    elements.append(Paragraph(
        f"adscrito a la: <u><b>{cliente}</b></u>",
        style_normal
    ))
    elements.append(Paragraph(
        "<font size='7' color='gray'>(Dirección/Subdirección/Departamento, Delegación, CCDI's)</font>",
        style_small
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    # Ubicación
    elements.append(Paragraph(
        f"Ubicación del lugar del equipo: <u><b>{ubicacion}</b></u>",
        style_normal
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # ========================================
    # DATOS DEL EQUIPO
    # ========================================
    # Descripción y Tipo
    equipo_header = [
        [
            Paragraph(f"Para el resguardo de el siguiente equipo de cómputo", style_normal),
            Paragraph(f"<u><b>{descripcion}</b></u>", style_bold),
            Paragraph("Tipo:", style_normal),
            Paragraph(f"<b>{tipo_equipo}</b>", style_bold)
        ],
        [
            '',
            Paragraph("<font size='7' color='gray'>(Descripción del equipo)</font>", style_small),
            '',
            Paragraph("<font size='7' color='gray'>(PC-Lap Top)</font>", style_small)
        ]
    ]
    eq_header_table = Table(equipo_header, colWidths=[3.2*inch, 1.3*inch, 0.6*inch, 1.2*inch])
    eq_header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(eq_header_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Serie, Modelo, Marca
    serie_data = [
        [
            Paragraph(f"y número de Serie: <u><b>{numero_serie}</b></u>", style_normal),
            Paragraph(f"Modelo: <u><b>{modelo}</b></u>", style_normal),
            Paragraph(f"Marca: <b>{marca}</b>", style_normal)
        ]
    ]
    serie_table = Table(serie_data, colWidths=[2.8*inch, 2*inch, 1.5*inch])
    serie_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(serie_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Procesador y Pantalla
    proc_data = [
        [
            Paragraph(f"Procesador: <b>{procesador}</b>", style_normal),
            Paragraph(f"Pantalla: <b>{pantalla}</b>", style_normal)
        ]
    ]
    proc_table = Table(proc_data, colWidths=[4*inch, 2.5*inch])
    proc_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(proc_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # RAM, Disco, DVD
    specs_data = [
        [
            Paragraph(f"Memoria Ram: <b>{memoria_ram}</b>", style_normal),
            Paragraph(f"Disco Duro: <b>{disco_duro}</b>", style_normal),
            Paragraph(f"DVD/RW: <b>{dvd_rw}</b>", style_normal)
        ]
    ]
    specs_table = Table(specs_data, colWidths=[2.3*inch, 2.3*inch, 1.7*inch])
    specs_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(specs_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Sistema Operativo
    elements.append(Paragraph(f"Sistema Operativo: <b>{sistema_operativo}</b>", style_normal))
    elements.append(Spacer(1, 0.4*inch))
    
    # ========================================
    # TEXTO LEGAL
    # ========================================
    texto_legal = """Este equipo de computo y accesorios, le es asignado para uso exclusivo del proyecto en el cual este trabajando y 
estara bajo su custodia y resguardo. Siendo responsabilidad del que suscribe cualquier daño físico, robo o perdida. 
El costo que se genere, por compostura o por recuperacion del mismo, debera ser pagado al valor actual del equipo."""
    
    style_legal = ParagraphStyle(
        'Legal',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        alignment=TA_CENTER,
        leading=12
    )
    elements.append(Paragraph(texto_legal, style_legal))
    elements.append(Spacer(1, 0.6*inch))
    
    # ========================================
    # FIRMAS
    # ========================================
    firma_data = [
        [
            Paragraph("<b>Entrego</b>", style_center),
            Paragraph("<b>Recibio</b>", style_center)
        ],
        [
            '',
            ''
        ],
        [
            Paragraph("_" * 25, style_center),
            Paragraph("_" * 25, style_center)
        ],
        [
            Paragraph(f"<b>{nombre_entrega}</b>", style_center),
            Paragraph(f"<b>{nombre_completo}</b>", style_center)
        ]
    ]
    
    firma_table = Table(firma_data, colWidths=[3.25*inch, 3.25*inch], rowHeights=[0.3*inch, 0.5*inch, 0.2*inch, 0.3*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(firma_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # ========================================
    # PIE DE PÁGINA
    # ========================================
    elements.append(Paragraph("_" * 95, ParagraphStyle('FooterLine', alignment=TA_CENTER, fontSize=6)))
    elements.append(Paragraph(
        "<font size='7'>Daniel Huacuja No 32 Col. Magisterial Vista Bella Tlalnepantla de Baz, Estado de Mexico C.P 54050. Tels.: 5359-4488 y 1663-0359</font>",
        ParagraphStyle('FooterAddress', alignment=TA_CENTER, fontSize=7)
    ))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer
