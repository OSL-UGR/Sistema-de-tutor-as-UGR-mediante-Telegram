import re
import logging

logger = logging.getLogger("horarios")
if not logger.handlers:
    handler = logging.FileHandler("horarios.log")
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def parsear_horario_string(horario_str):
    """Convierte un horario en formato string a diccionario"""
    if not horario_str:
        return {}
        
    horario_dict = {}
    try:
        for entrada in horario_str.split(';'):
            if not entrada.strip():
                continue
                
            dia, franjas_str = entrada.split(':', 1)
            franjas = [f.strip() for f in franjas_str.split(',')]
            horario_dict[dia.strip()] = franjas
            
        return horario_dict
    except Exception as e:
        logger.error(f"Error al parsear horario: {e}")
        return {}

def convertir_horario_a_string(horario_dict):
    """Convierte un diccionario de horario a formato string para DB"""
    if not horario_dict:
        return ""
        
    partes = []
    for dia, franjas in horario_dict.items():
        if franjas:  # Solo incluir días con franjas
            franjas_str = ", ".join(franjas)
            partes.append(f"{dia}: {franjas_str}")
            
    return "; ".join(partes)

def formatear_horario(horario_str):
    """Formatea un horario en string para mostrarlo al usuario"""
    if not horario_str or horario_str.strip() == "":
        return "No hay horario configurado."
        
    horario_dict = parsear_horario_string(horario_str)
    if not horario_dict:
        return "No hay horario configurado o el formato es inválido."
        
    resultado = []
    # Ordenar los días de la semana
    orden_dias = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
    dias_ordenados = sorted(horario_dict.keys(), key=lambda d: orden_dias.get(d, 99))
    
    for dia in dias_ordenados:
        franjas = horario_dict[dia]
        franjas_formateadas = [f"   • {franja}" for franja in franjas]
        resultado.append(f"📆 *{dia}*:\n" + "\n".join(franjas_formateadas))
        
    return "\n\n".join(resultado)