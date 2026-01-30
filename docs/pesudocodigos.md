3.4.1 Algoritmo de Cálculo de Ángulos
ALGORITMO CalcularAngulo(a, b, c)
CONVERTIR a, b, c a vectores numéricos
ba ← a - b
bc ← c - b
coseno ← (ba · bc) / (|ba| \* |bc|)
ANGULO ← arccos(coseno) en grados
RETORNAR ANGULO
FIN ALGORITMO

3.4.2 Algoritmo de Análisis de Video Completo

ALGORITMO AnalizarVideoCompleto(video, tipo_ejercicio)
ABRIR video
CREAR archivo temporal de salida
INICIALIZAR variables: fps, tamaño, frame_idx ← 0
MIENTRAS haya cuadros en el video HACER
LEER frame actual
CONVERTIR a RGB
DETECTAR pose con MediaPipe
SI se detecta pose ENTONCES
DIBUJAR landmarks
SEGÚN tipo_ejercicio: - sentadilla → AnalizarSentadilla - desplante → AnalizarDesplante - press banca → AnalizarPressBanca
ACTUALIZAR repeticiones y estadísticas
FIN SI
GUARDAR frame en video de salida
FIN MIENTRAS
RETORNAR ruta de salida y estadísticas
FIN ALGORITMO

3.4.3 Algoritmo de Análisis de Sentadilla
ALGORITMO AnalizarSentadilla(landmarks, frame, estado)
CALCULAR angulo_rodilla ← CalcularAnguloRodilla(landmarks)
CALCULAR angulo_espalda ← CalcularAnguloEspalda(landmarks)
score ← 100
SI angulo_rodilla > 130 Y estado = "bajando" → penalizar
SI angulo_rodilla < 70 → “demasiada profundidad”
SI angulo_espalda > 60 → “espalda muy inclinada”
SI rodillas desalineadas → “mantener nivel”
RETORNAR feedback, score
FIN ALGORITMO

3.4.4 Algoritmo de Análisis de Desplante
ALGORITMO AnalizarDesplante(landmarks)
CALCULAR angulo_rodilla_delantera ← CalcularAnguloRodilla(landmarks)
CALCULAR angulo_rodilla_trasera ← CalcularAnguloRodillaTrasera(landmarks)
score ← 100
SI angulo_rodilla_delantera < 70 → "rodilla muy adelantada"
SI angulo_rodilla_delantera > 110 → "baja más"
SI rodilla_delantera sobrepasa tobillo → "rodilla no debe pasar el tobillo"
SI rodilla_trasera no cerca del suelo → "baja más la rodilla trasera"
AJUSTAR score según desviaciones
RETORNAR feedback, score
FIN ALGORITMO

3.4.5 Algoritmo de Análisis de Press de Banca
ALGORITMO AnalizarPressBanca(landmarks)
CALCULAR angulo_codo_der ← CalcularAngulo(hombro_der, codo_der, muñeca_der)
CALCULAR angulo_codo_izq ← CalcularAngulo(hombro_izq, codo_izq, muñeca_izq)
score ← 100
SI angulo_codo_der < 50 → “demasiada profundidad”
SI diferencia entre brazos > 20° → “mantén simetría”
SI muñeca no alineada con hombro → “mantén trayectoria vertical”
RETORNAR feedback, score
FIN ALGORITMO

## """

-
-
-
-

"""

3.4.2 Algoritmo de Análisis de Desplante
Algoritmo AnalizarDesplante(landmarks)
ang_rod_del ← CalcularAnguloRodillaDelantera(landmarks)
ang_rod_tra ← CalcularAnguloRodillaTrasera(landmarks)
score ← 100
si ang_rod_del < 70 → feedback ← "Rodilla muy adelantada"; score -= 30
sino si 70 ≤ ang_rod_del < 80 → feedback ← "Cuidado con la rodilla"; score -= 15
sino si 80 ≤ ang_rod_del ≤ 100 → feedback ← "Ángulo correcto"; score += 5
sino si ang_rod_del > 110 → feedback ← "Baja más"; score -= 20
si rodilla_delantera_x > tobillo_x + 50px → feedback ← "Rodilla no debe pasar el tobillo"; score -= 25
si ang_rod_tra > 120 → feedback ← "Baja más la rodilla trasera"; score -= 15
RETORNAR feedback, score
FinAlgoritmo

3.4.3 Algoritmo de Análisis de Sentadilla
Algoritmo AnalizarSentadilla(landmarks, estado)
ang_rod ← CalcularAnguloRodilla(landmarks)
ang_esp ← CalcularAnguloEspalda(landmarks)
score ← 100
si ang_rod > 130 y estado = "bajando" → "Baja más"; score -= 15
si ang_rod < 70 → "Demasiada profundidad"; score -= 10
si 80 ≤ ang_rod ≤ 110 y estado = "bajando" → score += 5
si ang_esp > 60 → "Espalda muy inclinada"; score -= 30
sino si 45 < ang_esp ≤ 60 → "Mantén la espalda recta"; score -= 20
sino si 30 < ang_esp ≤ 45 → "Mejora postura de espalda"; score -= 10
si rodilla muy atrás/adelante del tobillo (eje X) → "Alinea rodilla con tobillo"; score -= 15..25
si |rodilla_izq_y - rodilla_der_y| > 30px → "Mantén rodillas niveladas"; score -= 10
RETORNAR feedback principal, score
FinAlgoritmo

3.4.4 Algoritmo de Análisis de Press de Banca
Algoritmo AnalizarPressBanca(landmarks)
ang_codo_der ← Angulo(hombro_der, codo_der, muñeca_der)
ang_codo_izq ← Angulo(hombro_izq, codo_izq, muñeca_izq)
score ← 100
si ang_codo_der < 50 → "Demasiada profundidad"; score -= 15
sino si 50 ≤ ang_codo_der < 60 → "Profundidad adecuada"; score += 5
sino si 60 ≤ ang_codo_der < 80 → "Puedes bajar más"; score -= 10
si ang_codo_der > 120 → "Baja más el peso"; score -= 20
si |ang_codo_der - ang_codo_izq| > 20° → "Mantén simetría"; score -= 15
sino si > 10° → "Leve asimetría"; score -= 5
si |muñeca_x - hombro_x| > 50px → "Mantén trayectoria vertical"; score -= 10
RETORNAR feedback principal, score
FinAlgoritmo

3.4.5 Algoritmo de Conteo de Repeticiones (Sentadilla)
Algoritmo ContarRepsSentadilla(angulo_rodilla, estado, bajo = 100, alto = 160)
si estado = "preparando" y angulo_rodilla < bajo → estado ← "bajando"
si estado = "bajando" y angulo_rodilla > alto → estado ← "preparando"; repeticiones++
RETORNAR estado, repeticiones
FinAlgoritmo

3.4.6 Algoritmo de Conteo de Repeticiones (Desplante)
Algoritmo ContarRepsDesplante(angulo_rodilla_delantera, estado, bajo = 80, alto = 140)
// bajo: rodilla flexionada (posición baja); alto: rodilla extendida (posición alta)
si estado = "preparando" y angulo_rodilla_delantera < bajo → estado ← "bajando"
si estado = "bajando" y angulo_rodilla_delantera > alto → estado ← "preparando"; repeticiones++
RETORNAR estado, repeticiones
FinAlgoritmo

3.4.7 Algoritmo de Conteo de Repeticiones (Press de Banca)
Algoritmo ContarRepsPressBanca(angulo_codo, estado, bajo = 80, alto = 120)
// bajo: fase inferior (codo más cerrado); alto: fase superior (codo más abierto)
si estado = "preparando" y angulo_codo < bajo → estado ← "bajando"
si estado = "bajando" y angulo_codo > alto → estado ← "preparando"; repeticiones++
RETORNAR estado, repeticiones
FinAlgoritmo
