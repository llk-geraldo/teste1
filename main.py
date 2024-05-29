import os
import sys
import cv2
import time
import json
import socket
import logging
import warnings
import threading
import subprocess
import numpy as np
from imutils.video import VideoStream
from datetime import datetime, timedelta
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

aux_flagCamera = False

def find_device(nomeDispositivo: str) -> int:
    try:
        result = subprocess.check_output("v4l2-ctl --list-devices", shell=True)
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError("Erro ao executar o comando 'v4l2-ctl'") from e

    result = str(result)
    video_list = result.split('\\n')
    if len([i for i in video_list if nomeDispositivo in i]) > 0:
        device_string = video_list[video_list.index([i for i in video_list if nomeDispositivo in i][0])+1]
        device_numbers = [int(i) for i in device_string if i.isdigit()]
        # Tratamento do valor se não encontrar o dispositivo no USB
        if len(device_numbers) > 0:
            if len(device_numbers) == 1:
                return device_numbers[-1]
            elif len(device_numbers) == 2:
                return device_numbers[-2] * 10 + device_numbers[-1]
        else:
            return -1
    else:
        return -1

while True:
    start = time.time()
    # Tentativa de conexão à câmera USB
    while aux_flagCamera == False:
        # Procura pela câmera USB
        DEVICE = find_device("Arducam")
        # Inicialização da câmera
        try:
            if DEVICE >=2:
                camera = VideoStream(src=DEVICE, usePiCamera=False, resolution=(1280, 720)).start()
                aux_flagCamera = camera.grabbed
            else:
                aux_flagCamera = False
        except:
            _, _, exception_traceback = sys.exc_info()
            print(f"Erro conexão câmera: {e} - {exception_traceback.tb_lineno}")
    # Sucesso na conexão à câmera USB
    try:
        image = camera.read()
        if image is not None:
            frame = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

            # Seleção de apenas um dos canais (canal R, assumindo BGR) da imagem
            _, _, frame = cv2.split(frame)

            # Corte do frame capturado
            frame = frame[1:1280-1, 1:720-1]

            # Segmentação do frame capturado pela câmera, com limiar T <= 0
            frameThreshold = cv2.inRange(frame, 255, 255)

            # Dilatação da imagem para ocultar furos
            frameThreshold = cv2.dilate(frameThreshold, np.ones((2,3), np.uint8), iterations=aux_params['dilatacao'])

            # Detecção da linha média do laser
            aux_linhaMedia = []
            aux_xLinha = []
            maximo = np.argmax(frameThreshold, axis=1)
            matriz_invertida_colunas = frameThreshold[:, ::-1]
            minimo = frameThreshold.shape[1] - 1 - np.argmax(matriz_invertida_colunas, axis=1)
            colunasSemLaser = 0
            for i in range(len(maximo)):
                if minimo[i] == frameThreshold.shape[1]-1 and maximo[i] == 0:
                    colunasSemLaser=colunasSemLaser+1
                else:
                    aux_linhaMedia.append((maximo[i]+minimo[i])//2)
                    aux_xLinha.append(i)

            # Análise de sujeira
            condicaoSujeira = (colunasSemLaser*100)/len(maximo)>=(100-80)
            condicaoPreviaSujeira = (colunasSemLaser*100)/len(maximo)>=((100-80)/2)

            # Atribuição do frame capturado para exibição
            aux_frameCaptura = cv2.merge([frame, frame, frame])

            if len(aux_linhaMedia)>0:
                for i in range(0, len(aux_xLinha)):
                    if int(aux_linhaMedia[i]-2)>0:
                        aux_frameCaptura[aux_xLinha[i]][int(aux_linhaMedia[i]-2):int(aux_linhaMedia[i]+2)] = [226, 172, 0]
                    elif int(aux_linhaMedia[i]-1)>0:
                        aux_frameCaptura[aux_xLinha[i]][int(aux_linhaMedia[i]-1):int(aux_linhaMedia[i]+2)] = [226, 172, 0]
                    elif int(aux_linhaMedia[i])>0:
                        aux_frameCaptura[aux_xLinha[i]][int(aux_linhaMedia[i]):int(aux_linhaMedia[i]+2)] = [226, 172, 0]
        
            # Atribuição do frame segmentado para exibição

    except Exception as e:
            _, _, exception_traceback = sys.exc_info()
            print(f"Erro processamento câmera: {e} - {exception_traceback.tb_lineno}")

    end = time.time()
    print(end - start)