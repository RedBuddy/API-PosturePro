import os
import cv2
import tempfile
import numpy as np
import mediapipe as mp
import math
from collections import deque  # suavizado por pierna

# Silencia logs verbosos de MediaPipe
try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except Exception:
    pass

def _new_writer_h264_or_fallback(output_path, fps, size):
    width, height = size
    # 1) Intentar H.264 (avc1)
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    writer = cv2.VideoWriter(output_path, fourcc, max(fps, 1), (width, height))
    if writer.isOpened():
        return writer, output_path, 'avc1'
    # 2) Fallback a mp4v
    base, _ = os.path.splitext(output_path)
    mp4v_path = base + '.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(mp4v_path, fourcc, max(fps, 1), (width, height))
    if writer.isOpened():
        return writer, mp4v_path, 'mp4v'
    # 3) ultimo recurso: AVI (XVID)
    avi_path = base + '.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(avi_path, fourcc, max(fps, 1), (width, height))
    return writer, avi_path, 'xvid'

class AnalizadorEjercicios:
    def __init__(self):
        # Configuracion de MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Inicializar detector de pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Landmarks
        self.HOMBROS = [self.mp_pose.PoseLandmark.LEFT_SHOULDER.value, self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        self.CODOS   = [self.mp_pose.PoseLandmark.LEFT_ELBOW.value,    self.mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        self.MUÑECAS = [self.mp_pose.PoseLandmark.LEFT_WRIST.value,    self.mp_pose.PoseLandmark.RIGHT_WRIST.value]
        self.CADERAS = [self.mp_pose.PoseLandmark.LEFT_HIP.value,      self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        self.RODILLAS= [self.mp_pose.PoseLandmark.LEFT_KNEE.value,     self.mp_pose.PoseLandmark.RIGHT_KNEE.value]
        self.TOBILLOS= [self.mp_pose.PoseLandmark.LEFT_ANKLE.value,    self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
    
    def calcular_angulo(self, a, b, c):
        a = np.array(a); b = np.array(b); c = np.array(c)
        ba = a - b; bc = c - b
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cosine_angle))
        return angle
    
    def analizar_video_completo(self, video_path, tipo_ejercicio='sentadilla', on_progress=None, progress_queue=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("No se pudo abrir el video de entrada")

        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        tmp_out = tempfile.mktemp(suffix='.mp4')
        writer, output_path, codec = _new_writer_h264_or_fallback(tmp_out, fps, (width, height))
        if not writer or not writer.isOpened():
            raise RuntimeError("No se pudo abrir VideoWriter con ningun codec disponible")

        stats = {
            'repeticiones': 0,
            'errores_detectados': [],
            'scores_por_frame': [],
            'duracion_segundos': (total_frames / fps) if fps > 0 and total_frames > 0 else 0,
            'score_promedio': 0
        }

        # Helper para notificar progreso
        def _notify_progress(pct: int):
            try:
                if on_progress:
                    on_progress(int(pct))
                if progress_queue is not None:
                    # Por ejemplo, una queue.Queue o asyncio.Queue
                    progress_queue.put_nowait(int(pct))
            except Exception:
                pass

        frame_idx = 0
        estado_ejercicio = "preparando"
        repeticiones = 0
        umbral_angulo_bajo = 100
        umbral_angulo_alto = 160
        # Estado interno para desplantes
        self._lunge_prev_angle = None
        self._lunge_min_angle = None
        self._lunge_front_side = None
        self._knee_buffers = {'izq': deque(maxlen=7), 'der': deque(maxlen=7)}
        last_progress = -1
        # Antispam de errores
        last_error_msg = None
        last_error_ts = -1.0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            timestamp = frame_idx / fps

            # Progreso basado en total de frames (si esta disponible)
            if total_frames > 0:
                progress = int((frame_idx / total_frames) * 100)
                if progress != last_progress:
                    _notify_progress(progress)
                    last_progress = progress

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(255, 0, 0), thickness=2)
                )

                landmarks = results.pose_landmarks.landmark
                feedback_data = {"feedback": "", "score": 100, "color": (0, 255, 0)}

                if tipo_ejercicio == 'sentadilla':
                    feedback_data = self.analizar_sentadilla_completo(landmarks, frame, estado_ejercicio, timestamp)
                    angulo_rodilla = self.calcular_angulo_rodilla(landmarks)
                    if angulo_rodilla is not None:
                        if estado_ejercicio == "preparando" and angulo_rodilla < umbral_angulo_bajo:
                            estado_ejercicio = "bajando"
                        elif estado_ejercicio == "bajando" and angulo_rodilla > umbral_angulo_alto:
                            estado_ejercicio = "preparando"
                            repeticiones += 1
                            stats['repeticiones'] = repeticiones
                elif tipo_ejercicio == 'desplantes':
                    feedback_data = self.analizar_desplantes_completo(landmarks, frame, timestamp, estado_ejercicio)
                    # 1) Ángulos crudos
                    izq, der = self.calcular_angulos_rodillas(landmarks)
                    # 2) Suavizado por pierna (mediana)
                    if izq is not None: self._knee_buffers['izq'].append(izq)
                    if der is not None: self._knee_buffers['der'].append(der)
                    def _med(side):
                        buf = self._knee_buffers[side]
                        return float(np.median(buf)) if len(buf) else None
                    izq_s, der_s = _med('izq'), _med('der')
                    # 3) Fijar pierna delantera durante la repetición
                    if estado_ejercicio == "preparando" or self._lunge_front_side is None:
                        if izq_s is not None and der_s is not None:
                            self._lunge_front_side = 'izq' if izq_s <= der_s else 'der'
                        elif izq_s is not None:
                            self._lunge_front_side = 'izq'
                        elif der_s is not None:
                            self._lunge_front_side = 'der'
                        else:
                            self._lunge_front_side = None
                    front_side = self._lunge_front_side
                    front_angle_s = izq_s if front_side == 'izq' else der_s if front_side == 'der' else None
                    # 4) Maquina de estados robusta con histéresis
                    if front_angle_s is not None:
                        if self._lunge_prev_angle is None:
                            self._lunge_prev_angle = front_angle_s
                        delta = front_angle_s - self._lunge_prev_angle
                        self._lunge_prev_angle = front_angle_s
                        bajando_trend = delta < -0.3   # disminuye el ángulo
                        subiendo_trend = delta >  0.3  # aumenta el ángulo
                        # Umbrales
                        start_thresh = 165   # iniciar bajada
                        depth_ok     = 115   # fondo válido alcanzado
                        top_thresh   = 172   # parte alta
                        if estado_ejercicio == "preparando":
                            if front_angle_s < start_thresh and bajando_trend:
                                estado_ejercicio = "bajando"
                                self._lunge_min_angle = front_angle_s
                        elif estado_ejercicio == "bajando":
                            self._lunge_min_angle = min(self._lunge_min_angle or front_angle_s, front_angle_s)
                            # Solo pasar a subiendo si ya tocamos fondo suficiente
                            if subiendo_trend and (self._lunge_min_angle is not None and self._lunge_min_angle < depth_ok):
                                estado_ejercicio = "subiendo"
                        elif estado_ejercicio == "subiendo":
                            if front_angle_s > top_thresh and subiendo_trend:
                                if (self._lunge_min_angle or 999) < depth_ok:
                                    repeticiones += 1
                                    stats['repeticiones'] = repeticiones
                                estado_ejercicio = "preparando"
                                self._lunge_min_angle = None
                                self._lunge_prev_angle = None
                                self._lunge_front_side = None
                elif tipo_ejercicio == 'press_banca':
                    feedback_data = self.analizar_press_banca_completo(landmarks, frame, timestamp)
                
                # NUEVO: overlay + registro de metricas
                frame = self.agregar_overlay_feedback(frame, feedback_data, repeticiones, timestamp, estado_ejercicio)
                stats['scores_por_frame'].append(feedback_data['score'])
                if feedback_data.get('feedback') and feedback_data['score'] < 80:
                    # Evitar registrar el mismo error en cada frame (cooldown 0.5s)
                    if feedback_data['feedback'] != last_error_msg or (timestamp - last_error_ts) >= 0.5:
                        stats['errores_detectados'].append({
                            'timestamp': float(f"{timestamp:.2f}"),
                            'error': feedback_data['feedback']
                        })
                        last_error_msg = feedback_data['feedback']
                        last_error_ts = timestamp
            else:
                cv2.putText(frame, "No se detecta persona", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # NUEVO: escribir siempre el frame (haya o no landmarks)
            writer.write(frame)

        cap.release()
        writer.release()

        # Asegurar 100% al finalizar
        if last_progress < 100:
            _notify_progress(100)

        if stats['scores_por_frame']:
            stats['score_promedio'] = float(np.mean(stats['scores_por_frame']))
        else:
            stats['score_promedio'] = 0.0

        # Duracion real si no venia en metadata
        if not stats['duracion_segundos']:
            stats['duracion_segundos'] = frame_idx / fps if fps > 0 else 0

        # NUEVO: recomendaciones personalizadas
        stats['recomendaciones'] = self.generar_recomendaciones(stats, tipo_ejercicio)

        return output_path, stats
    
    def agregar_overlay_feedback(self, frame, feedback_data, repeticiones, timestamp, estado):
        height, width = frame.shape[:2]
        panel_width = 350; panel_height = 180
        panel_x = width - panel_width - 10; panel_y = 10
        
        overlay = frame.copy()
        import cv2 as _cv2
        _cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_width, panel_y + panel_height), (40, 40, 40), -1)
        frame = _cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        _cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_width, panel_y + panel_height), feedback_data['color'], 2)
        _cv2.putText(frame, "ANALISIS EN VIVO", (panel_x + 10, panel_y + 25), _cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        _cv2.putText(frame, f"Score: {feedback_data['score']}/100", (panel_x + 10, panel_y + 55), _cv2.FONT_HERSHEY_SIMPLEX, 0.7, feedback_data['color'], 2)
        _cv2.putText(frame, f"Repeticiones: {repeticiones}", (panel_x + 10, panel_y + 85), _cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        minutos = int(timestamp // 60); segundos = int(timestamp % 60)
        _cv2.putText(frame, f"Tiempo: {minutos:02d}:{segundos:02d}", (panel_x + 10, panel_y + 115), _cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        _cv2.putText(frame, f"Estado: {estado}", (panel_x + 10, panel_y + 145), _cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        if feedback_data['feedback']:
            for i, line in enumerate(self.dividir_texto(feedback_data['feedback'], 40)):
                _cv2.putText(frame, line, (panel_x, panel_y + panel_height + 30 + i * 25), _cv2.FONT_HERSHEY_SIMPLEX, 0.6, feedback_data['color'], 2)
        return frame
    
    def dividir_texto(self, texto, max_chars):
        if len(texto) <= max_chars:
            return [texto]
        words = texto.split(); lines = []; current_line = ""
        for word in words:
            if len((current_line + " " + word).strip()) <= max_chars:
                current_line = (current_line + " " + word).strip()
            else:
                if current_line: lines.append(current_line)
                current_line = word
        if current_line: lines.append(current_line)
        return lines
    
    def crear_frame_resumen(self, estadisticas, width, height, tipo_ejercicio):
        import cv2 as _cv2
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            intensity = int(30 + (i / height) * 20)
            frame[i, :] = [intensity, intensity, intensity]
        _cv2.putText(frame, "RESUMEN DEL EJERCICIO", (50, 80), _cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        _cv2.putText(frame, f"Ejercicio: {tipo_ejercicio.replace('_', ' ').title()}", (50, 130), _cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        y_pos = 180
        _cv2.putText(frame, f"Repeticiones completadas: {estadisticas['repeticiones']}", (50, y_pos), _cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2); y_pos += 40
        score_color = (0, 255, 0) if estadisticas['score_promedio'] >= 80 else (0, 165, 255) if estadisticas['score_promedio'] >= 60 else (0, 0, 255)
        _cv2.putText(frame, f"Score promedio: {estadisticas['score_promedio']:.1f}/100", (50, y_pos), _cv2.FONT_HERSHEY_SIMPLEX, 0.7, score_color, 2); y_pos += 40
        minutos = int(estadisticas['duracion_segundos'] // 60); segundos = int(estadisticas['duracion_segundos'] % 60)
        _cv2.putText(frame, f"Duracion: {minutos:02d}:{segundos:02d}", (50, y_pos), _cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2); y_pos += 60
        if estadisticas['errores_detectados']:
            _cv2.putText(frame, "Principales areas de mejora:", (50, y_pos), _cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2); y_pos += 35
            errores_count = {}
            for e in estadisticas['errores_detectados']:
                msg = e['error']; errores_count[msg] = errores_count.get(msg, 0) + 1
            for error, count in sorted(errores_count.items(), key=lambda x: x[1], reverse=True)[:3]:
                _cv2.putText(frame, f"• {error} ({count} veces)", (70, y_pos), _cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1); y_pos += 30
        return frame
    
    def analizar_sentadilla_completo(self, landmarks, frame, estado, timestamp):
        h, w, _ = frame.shape
        angulo_rodilla = self.calcular_angulo_rodilla(landmarks)
        angulo_espalda = self.calcular_angulo_espalda(landmarks)
        score = 100; feedback_messages = []; color = (0, 255, 0)
        if angulo_rodilla is not None:
            cv2.putText(frame, f"Rodilla: {angulo_rodilla:.1f}°", (w - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        if angulo_espalda is not None:
            cv2.putText(frame, f"Espalda: {angulo_espalda:.1f}°", (w - 200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        if angulo_rodilla is not None:
            if angulo_rodilla > 130 and estado == "bajando":
                feedback_messages.append("Baja mas la sentadilla"); score -= 15; color = (0, 165, 255)
            elif angulo_rodilla < 70:
                feedback_messages.append("Demasiada profundidad"); score -= 10; color = (0, 100, 255)
            elif 80 <= angulo_rodilla <= 110 and estado == "bajando":
                score += 5
        if angulo_espalda is not None:
            if angulo_espalda > 60:
                feedback_messages.append("Espalda muy inclinada!"); score -= 30; color = (0, 0, 255)
            elif angulo_espalda > 45:
                feedback_messages.append("Manten la espalda recta"); score -= 20; color = (0, 100, 255)
            elif angulo_espalda > 30:
                feedback_messages.append("Mejora postura de espalda"); score -= 10; color = (0, 165, 255)
        if angulo_rodilla is not None and angulo_rodilla < 120:
            rodilla_x = landmarks[self.RODILLAS[1]].x * w; tobillo_x = landmarks[self.TOBILLOS[1]].x * w
            if rodilla_x < tobillo_x - 50:
                feedback_messages.append("Rodillas muy atras"); score -= 15; color = (0, 0, 255)
            elif rodilla_x > tobillo_x + 100:
                feedback_messages.append("Rodillas muy adelante!"); score -= 25; color = (0, 0, 255)
        try:
            rodilla_izq = landmarks[self.RODILLAS[0]].y * h; rodilla_der = landmarks[self.RODILLAS[1]].y * h
            if abs(rodilla_izq - rodilla_der) > 30:
                feedback_messages.append("Manten rodillas niveladas"); score -= 10
                if color == (0, 255, 0): color = (0, 165, 255)
        except:
            pass
        main_feedback = "Excelente forma!" if not feedback_messages else feedback_messages[0]
        return {"feedback": main_feedback, "score": max(0, min(100, score)), "color": color}
    
    def analizar_press_banca_completo(self, landmarks, frame, timestamp):
        h, w, _ = frame.shape
        hombro_der = [landmarks[self.HOMBROS[1]].x, landmarks[self.HOMBROS[1]].y]
        codo_der   = [landmarks[self.CODOS[1]].x,   landmarks[self.CODOS[1]].y]
        muñeca_der = [landmarks[self.MUÑECAS[1]].x, landmarks[self.MUÑECAS[1]].y]
        hombro_izq = [landmarks[self.HOMBROS[0]].x, landmarks[self.HOMBROS[0]].y]
        codo_izq   = [landmarks[self.CODOS[0]].x,   landmarks[self.CODOS[0]].y]
        muñeca_izq = [landmarks[self.MUÑECAS[0]].x, landmarks[self.MUÑECAS[0]].y]
        
        angulo_codo_der = None; angulo_codo_izq = None
        if all(not math.isnan(p[0]) for p in [hombro_der, codo_der, muñeca_der]):
            angulo_codo_der = self.calcular_angulo(hombro_der, codo_der, muñeca_der)
        if all(not math.isnan(p[0]) for p in [hombro_izq, codo_izq, muñeca_izq]):
            angulo_codo_izq = self.calcular_angulo(hombro_izq, codo_izq, muñeca_izq)
        
        score = 100; feedback_messages = []; color = (0, 255, 0)
        if angulo_codo_der is not None:
            cv2.putText(frame, f"Codo Der: {angulo_codo_der:.1f}°", (w - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            if angulo_codo_der < 50:
                feedback_messages.append("Demasiada profundidad"); score -= 15; color = (0, 100, 255)
            elif angulo_codo_der < 60:
                feedback_messages.append("Profundidad adecuada"); score += 5
            elif angulo_codo_der < 80:
                feedback_messages.append("Puedes bajar mas"); score -= 10; color = (0, 165, 255)
            elif angulo_codo_der > 120:
                feedback_messages.append("Baja mas el peso"); score -= 20; color = (0, 0, 255)
        if angulo_codo_der is not None and angulo_codo_izq is not None:
            cv2.putText(frame, f"Codo Izq: {angulo_codo_izq:.1f}°", (w - 200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            diferencia_brazos = abs(angulo_codo_der - angulo_codo_izq)
            if diferencia_brazos > 20:
                feedback_messages.append("Manten simetria entre brazos"); score -= 15
                if color == (0, 255, 0): color = (0, 165, 255)
            elif diferencia_brazos > 10:
                feedback_messages.append("Leve asimetria en brazos"); score -= 5
                if color == (0, 255, 0): color = (0, 200, 255)
        try:
            muñeca_der_x = landmarks[self.MUÑECAS[1]].x * w
            hombro_der_x = landmarks[self.HOMBROS[1]].x * w
            if abs(muñeca_der_x - hombro_der_x) > 50:
                feedback_messages.append("Manten trayectoria vertical"); score -= 10
                if color == (0, 255, 0): color = (0, 165, 255)
        except:
            pass
        main_feedback = "Buen movimiento!" if not feedback_messages else feedback_messages[0]
        return {"feedback": main_feedback, "score": max(0, min(100, score)), "color": color}
    
    def calcular_angulo_rodilla(self, landmarks):
        cadera  = [landmarks[self.CADERAS[1]].x,  landmarks[self.CADERAS[1]].y]
        rodilla = [landmarks[self.RODILLAS[1]].x, landmarks[self.RODILLAS[1]].y]
        tobillo = [landmarks[self.TOBILLOS[1]].x, landmarks[self.TOBILLOS[1]].y]
        if all(not math.isnan(p[0]) for p in [cadera, rodilla, tobillo]):
            return self.calcular_angulo(cadera, rodilla, tobillo)
        return None
    
    def calcular_angulo_espalda(self, landmarks):
        """
        Ángulo del torso respecto a la vertical (0° = torso recto, mayor = más inclinado).
        Usa eje vertical global y suaviza con mediana para reducir jitter.
        """
        hombro = [landmarks[self.HOMBROS[1]].x, landmarks[self.HOMBROS[1]].y]
        cadera = [landmarks[self.CADERAS[1]].x, landmarks[self.CADERAS[1]].y]

        if any(math.isnan(p) for p in [hombro[0], hombro[1], cadera[0], cadera[1]]):
            return None

        # Vector torso (de cadera a hombro)
        vx = hombro[0] - cadera[0]
        vy = hombro[1] - cadera[1]   # Nota: en MediaPipe y aumenta hacia abajo
        norm = math.sqrt(vx*vx + vy*vy)
        if norm < 1e-6:
            return None

        # Eje vertical hacia arriba en coordenadas normalizadas (0, -1)
        # cos(theta) = (v · (0,-1)) / |v| = (-vy)/|v|
        cos_theta = (-vy) / norm
        cos_theta = max(-1.0, min(1.0, cos_theta))
        angle_deg = math.degrees(math.acos(cos_theta))  # 0° recto, >0 inclinado

        # Suavizado (mediana últimos 5 valores)
        if not hasattr(self, "_espalda_angle_buffer"):
            self._espalda_angle_buffer = []
        self._espalda_angle_buffer.append(angle_deg)
        if len(self._espalda_angle_buffer) > 5:
            self._espalda_angle_buffer.pop(0)
        angle_smoothed = float(np.median(self._espalda_angle_buffer))

        return angle_smoothed

    def calcular_flexion_toracolumbar(self, landmarks):
        """
        Proxy de 'redondeo' (flexión torácica) usando relación entre:
        - Vector tronco (cadera media -> hombro medio)
        - Vector cuello/cabeza (hombro medio -> oreja/nariz)
        Devuelve diferencia angular (grados). Mayor = más flexión anterior.
        """
        try:
            ls = landmarks[self.HOMBROS[0]]; rs = landmarks[self.HOMBROS[1]]
            lh = landmarks[self.CADERAS[0]]; rh = landmarks[self.CADERAS[1]]
            # Preferir orejas; si faltan usar nariz
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            le_idx = self.mp_pose.PoseLandmark.LEFT_EAR.value
            re_idx = self.mp_pose.PoseLandmark.RIGHT_EAR.value
            le = landmarks[le_idx]; re = landmarks[re_idx]

            mid_shoulder = ((ls.x + rs.x)/2, (ls.y + rs.y)/2)
            mid_hip      = ((lh.x + rh.x)/2, (lh.y + rh.y)/2)

            # Cabeza (usar orejas si tienen visibilidad decente, si no nariz)
            head_pts = []
            for pt in (le, re):
                if pt.visibility > 0.5:
                    head_pts.append((pt.x, pt.y))
            if head_pts:
                head = (sum(p[0] for p in head_pts)/len(head_pts),
                        sum(p[1] for p in head_pts)/len(head_pts))
            else:
                head = (nose.x, nose.y)

            vx_trunk = mid_shoulder[0] - mid_hip[0]
            vy_trunk = mid_shoulder[1] - mid_hip[1]
            vx_neck  = head[0] - mid_shoulder[0]
            vy_neck  = head[1] - mid_shoulder[1]

            def _norm(vx, vy):
                n = math.sqrt(vx*vx + vy*vy)
                return (vx/n, vy/n) if n > 1e-6 else (0,0)

            tx, ty = _norm(vx_trunk, vy_trunk)
            nx, ny = _norm(vx_neck, vy_neck)

            dot = max(-1.0, min(1.0, tx*nx + ty*ny))
            angle = math.degrees(math.acos(dot))  # 0 alineado, > grande = más flexión

            # Suavizado corto
            if not hasattr(self, "_flex_buffer"):
                self._flex_buffer = []
            self._flex_buffer.append(angle)
            if len(self._flex_buffer) > 5:
                self._flex_buffer.pop(0)
            return float(np.median(self._flex_buffer))
        except Exception:
            return None

    def analizar_desplantes_completo(self, landmarks, frame, timestamp, estado):
        """
        Analiza desplantes (lunges) usando:
        - Flexión de rodilla de la pierna delantera (ideal ~80–110° en el fondo).
        - Alineación rodilla-tobillo (evitar muy adelante/atrás).
        - Inclinación del torso (ángulo de espalda respecto a la vertical).
        """
        h, w, _ = frame.shape
        izq, der = self.calcular_angulos_rodillas(landmarks)
        angulo_espalda = self.calcular_angulo_espalda(landmarks)

        # Determinar pierna delantera por mayor flexión (menor ángulo)
        front_side = None
        front_knee = None
        if izq is not None and der is not None:
            if izq <= der:
                front_side, front_knee = 'izq', izq
            else:
                front_side, front_knee = 'der', der
        elif izq is not None:
            front_side, front_knee = 'izq', izq
        elif der is not None:
            front_side, front_knee = 'der', der

        # Suavizado de rodilla delantera (mediana 7 frames)
        front_knee_s = None
        if front_knee is not None:
            if not hasattr(self, "_front_knee_buffer"):
                self._front_knee_buffer = []
            self._front_knee_buffer.append(front_knee)
            if len(self._front_knee_buffer) > 7:
                self._front_knee_buffer.pop(0)
            front_knee_s = float(np.median(self._front_knee_buffer))
        
        # Heurística: rodilla trasera “casi al piso” => no pedir bajar más
        near_floor = False
        try:
            if front_side == 'izq':
                back_knee = landmarks[self.RODILLAS[1]]
                back_ankle = landmarks[self.TOBILLOS[1]]
            elif front_side == 'der':
                back_knee = landmarks[self.RODILLAS[0]]
                back_ankle = landmarks[self.TOBILLOS[0]]
            else:
                back_knee = back_ankle = None
            if back_knee and back_ankle:
                knee_y = back_knee.y * h
                ankle_y = back_ankle.y * h
                # Umbral relativo al alto (6% de la altura o ~35px mínimo)
                thr = max(35, 0.06 * h)
                near_floor = abs(ankle_y - knee_y) < thr
        except Exception:
            near_floor = False

        score = 100
        feedback_messages = []
        color = (0, 255, 0)

        # Overlay info básica
        if izq is not None:
            cv2.putText(frame, f"Rodilla IZQ: {izq:.1f}°", (w - 220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        if der is not None:
            cv2.putText(frame, f"Rodilla DER: {der:.1f}°", (w - 220, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        if angulo_espalda is not None:
            cv2.putText(frame, f"Torso: {angulo_espalda:.1f}°", (w - 220, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Torso verticalidad
        if angulo_espalda is not None:
            if angulo_espalda > 35:
                feedback_messages.append("Torso muy inclinado"); score -= 20; color = (0, 0, 255)
            elif angulo_espalda > 25:
                feedback_messages.append("Mantén el torso más erguido"); score -= 10; color = (0, 165, 255)

        # Profundidad/front knee
        if front_knee_s is not None:
            # Solo sugerir “baja más” mientras se está bajando
            if estado == "bajando" and front_knee_s > 140 and not near_floor:
                feedback_messages.append("Baja un poco más"); score -= 8; color = (0, 165, 255)
            elif front_knee_s < 55:
                feedback_messages.append("Demasiada profundidad"); score -= 10; color = (0, 100, 255)

        # Alineación rodilla-tobillo de la pierna delantera
        try:
            if front_side == 'izq':
                knee = landmarks[self.RODILLAS[0]]
                ankle = landmarks[self.TOBILLOS[0]]
            elif front_side == 'der':
                knee = landmarks[self.RODILLAS[1]]
                ankle = landmarks[self.TOBILLOS[1]]
            else:
                knee = ankle = None

            knee_x = knee.x * w if knee else None
            knee_y = knee.y * h if knee else None
            ankle_x = ankle.x * w if ankle else None
            ankle_y = ankle.y * h if ankle else None

            if knee_x is not None and ankle_x is not None and knee_y is not None and ankle_y is not None:
                # Normalizar desplazamiento horizontal por la longitud de la tibia (en píxeles)
                dx_px = knee_x - ankle_x
                dy_px = knee_y - ankle_y
                tibia_px = math.hypot(dx_px, dy_px)
                if tibia_px > 1e-6:
                    dx_norm = dx_px / tibia_px  # ~0 = alineado; + grande = rodilla más adelante; - grande = más atrás

                    # Evaluar solo en fase baja y sin near_floor para evitar falsos positivos
                    if estado == "bajando" and (front_knee_s is not None and front_knee_s < 140) and not near_floor:
                        # Umbrales más tolerantes (válidos para desplante al frente o atrás)
                        if dx_norm > 0.45:
                            feedback_messages.append("Rodilla delantera muy adelante"); score -= 12; color = (0, 165, 255)
                        elif dx_norm < -0.25:
                            feedback_messages.append("Rodilla delantera muy atrás"); score -= 8; color = (0, 165, 255)
        except Exception:
            pass

        # Asimetría entre piernas en el fondo
        if izq is not None and der is not None:
            if abs(izq - der) > 25:
                feedback_messages.append("Asimetría entre piernas"); score -= 10
                if color == (0, 255, 0): color = (0, 165, 255)

        main_feedback = "Buen desplante!" if not feedback_messages else feedback_messages[0]
        return {"feedback": main_feedback, "score": max(0, min(100, score)), "color": color}

    def calcular_angulos_rodillas(self, landmarks):
        """
        Devuelve (angulo_rodilla_izq, angulo_rodilla_der) en grados.
        """
        try:
            cadera_i  = [landmarks[self.CADERAS[0]].x,  landmarks[self.CADERAS[0]].y]
            rodilla_i = [landmarks[self.RODILLAS[0]].x, landmarks[self.RODILLAS[0]].y]
            tobillo_i = [landmarks[self.TOBILLOS[0]].x, landmarks[self.TOBILLOS[0]].y]
            ang_i = self.calcular_angulo(cadera_i, rodilla_i, tobillo_i) if all(not math.isnan(p[0]) for p in [cadera_i, rodilla_i, tobillo_i]) else None
        except Exception:
            ang_i = None
        try:
            cadera_d  = [landmarks[self.CADERAS[1]].x,  landmarks[self.CADERAS[1]].y]
            rodilla_d = [landmarks[self.RODILLAS[1]].x, landmarks[self.RODILLAS[1]].y]
            tobillo_d = [landmarks[self.TOBILLOS[1]].x, landmarks[self.TOBILLOS[1]].y]
            ang_d = self.calcular_angulo(cadera_d, rodilla_d, tobillo_d) if all(not math.isnan(p[0]) for p in [cadera_d, rodilla_d, tobillo_d]) else None
        except Exception:
            ang_d = None
        return ang_i, ang_d
    
    def generar_recomendaciones(self, stats, tipo_ejercicio: str):
        # Conteo de errores
        counts = {}
        for e in stats.get('errores_detectados', []):
            msg = (e.get('error') or '').strip()
            if not msg:
                continue
            counts[msg] = counts.get(msg, 0) + 1

        if not counts:
            return ["Excelente técnica general. Continúa igual."]

        advice_map = {
            "espalda muy inclinada": "Mantén el torso más erguido. Activa el core, eleva el pecho y mira al frente.",
            "torso muy inclinado": "Mantén el torso más erguido. Activa el core y estabiliza la pelvis.",
            "manten la espalda recta": "Neutraliza la columna. Aprieta abdomen y evita redondear la zona lumbar.",
            "mejora postura de espalda": "Retracción escapular y pecho arriba para estabilizar la espalda.",
            "baja mas la sentadilla": "Busca ~90° en rodillas. Abre ligeramente la base y controla la bajada.",
            "baja un poco más": "Flexiona más la rodilla delantera hasta ~90° manteniendo el talón apoyado.",
            "demasiada profundidad": "Evita perder tensión al fondo. Mantén control sin colapsar la pelvis.",
            "rodillas muy adelante": "Cadera atrás y peso medio del pie. Alinea rodillas con la punta del pie.",
            "rodillas muy atras": "Conduce las rodillas hacia adelante siguiendo la punta del pie.",
            "rodilla delantera muy adelante": "Acorta el paso o lleva la cadera atrás para alinear rodilla con tobillo.",
            "rodilla delantera muy atrás": "Adelanta ligeramente la rodilla para centrarla sobre el tobillo.",
            "manten rodillas niveladas": "Evita valgo/varo. Empuja simétrico con ambos pies.",
            "asimetría entre piernas": "Equilibra la carga entre ambas piernas y controla la profundidad.",
            "extiende completamente caderas": "Bloquea la cadera al final apretando glúteos.",
            "manten trayectoria vertical": "Recorre la barra en línea vertical sobre muñeca/hombro.",
            "manten simetria entre brazos": "Empuja ambos lados a la vez. Usa carga que permita control.",
            "leve asimetria en brazos": "Sincroniza la fase concéntrica con enfoque en el brazo rezagado.",
        }

        # Top 3 errores más frecuentes
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]

        recs = []
        for err, _ in top:
            key = err.lower()
            chosen = None
            for k, adv in advice_map.items():
                if k in key:
                    chosen = adv
                    break
            recs.append(chosen or f"Atiende: {err}")

        # Ajuste por score global
        avg = stats.get('score_promedio', 0)
        if avg < 60:
            recs.append("Reduce la velocidad, graba con buena luz y encuadre para mejorar detección y control técnico.")
        elif avg >= 80 and len(recs) == 1:
            recs.append("Mantén la técnica y progresa gradualmente la carga/volumen.")

        # Únicas y máximo 3–4
        dedup = []
        for r in recs:
            if r not in dedup:
                dedup.append(r)
        return dedup[:4]

# Instancia unica
analyzer = AnalizadorEjercicios()