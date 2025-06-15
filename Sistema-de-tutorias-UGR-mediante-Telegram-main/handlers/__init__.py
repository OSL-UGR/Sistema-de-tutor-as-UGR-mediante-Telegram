# filepath: C:\Users\Alberto\Desktop\TFG_V2\main.py
import telebot
import time
import threading
from telebot import types
import os
import sys
from config import TOKEN, DB_PATH

"""
Paquete de handlers para el bot de tutorías UGR.
"""
# Este archivo debe ser simple para evitar importaciones circulares

# Solo incluye variables compartidas si son necesarias
user_states = {}
user_data = {}
estados_timestamp = {}

