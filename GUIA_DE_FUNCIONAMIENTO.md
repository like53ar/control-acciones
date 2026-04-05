# 🧘‍♂️ Guía de Funcionamiento - Portafolio Zen

Bienvenido al manual oficial de uso de **Portafolio Zen**. Este documento te guiará paso a paso en el uso de la plataforma para llevar el control total de tus inversiones directamente desde tu entorno local.

---

## 1. Inicio del Sistema

Para iniciar el sistema:
1. Dirígete a la carpeta principal `control-acciones`.
2. Haz doble clic en el archivo llamado `launcher.vbs`.
3. Verás una pantalla de carga (Splash Screen) mientras el sistema enciende de fondo (servidor y la interfaz gráfica).
4. El sistema se abrirá en tu navegador de forma automática en la dirección `http://localhost:4200`.

---

## 2. Descripción de la Interfaz Principal

La interfaz está dividida en varias partes clave:

* **Ticker Tape Superior:** Una cinta o barra en la parte de arriba que corre en todo momento. Te informará del precio actual (en tiempo real) de los principales índices del mundo (S&P 500, Nasdaq), las empresas más importantes, criptomonedas (Bitcoin, Ethereum), entre otros.
* **Panel Consolidado:** Es la tabla principal donde puedes ver tu "Portafolio". Cada vez que agregues compras sobre una misma empresa o criptomoneda, la plataforma consolidará todo en una sola línea, permitiéndote ver de forma limpia y directa detalles como: dinero total invertido, variación general del precio y valoración actual.
* **Ventana de Gráficos:** Para habilitar una revisión visual, acá es donde encuentras la distribución en gráfico de torta y una curva evolutiva de tu rendimiento basada en análisis diarios.

---

## 3. Cargar una Inversión o Compra

1. Ve a la sección del Portafolio y busca el botón de **Nueva Posición** o **Nueva Compra**.
2. Escribe el Símbolo (Tícker) de la acción o moneda. El sistema te recomendará opciones (ej. Para Apple, escribe *AAPL*; para ciertos Cedears a veces varía la denominación, para criptos usa el sufijo adecuado o guíate por el autocompletado de Yahoo Finance).
3. Introduce la Cantidad comprada.
4. Digita el Precio de compra (precio que pagaste).
5. Confirma y guarda.

---

## 4. Registro y Venta de Activos

Si vendes un activo o parte de este:
1. En la tabla principal al lado de cada posición, encontrarás las opciones de control.
2. Es sumamente importante utilizar la opción **Vender (Registrar Venta Real)** para cerrar una posición de forma correcta, dejando registro histórico para el análisis posterior. 
3. *Aviso importante:* Si pulsas en "eliminar", se borrará el registro completo (ideal si te equivocaste tipeando algo, pero no lo uses si estás concretando una venta que quieres que quede en el historial de ganancia/pérdida).

---

## 5. El Cierre del Día (Históricos y Tendencias)

Tu plataforma captura datos constantemente, pero cuenta con un sistema de "histórico inteligente":
* **Automático:** A las 21:00 hs ARG (17:00 EST), el portafolio va a "sacar una foto" de final del día para guardar tus ganancias o bajadas.
* **Manual:** También cuentas con la herramienta de **"Cierre del día"** si quieres forzar esa "captura o foto" instantánea en cualquier otro horario, dejando los datos grabados para las estadísticas.

Con el tiempo acumulado de los históricos, el Panel de Gráficos se volverá más alimentado y podrás ver el rendimiento y promedios.

---

## 6. Monedas y Conversiones

Portafolio Zen usa lo que se llama un **Oráculo Cripto**, lo que significa que de fondo se conecta a los valores libres (mediante Binance) para estimar valores reales del dólar a la hora de convertir (USDT/ARS en vivo). Esto hace que tu panorama general en pesos o equivalentes cuente con un precio mucho más justo o cercano a la realidad financiera que el oficial.

---

## 7. Notas Adicionales sobre la Seguridad

* **Totalmente Privado:** Nadie más puede acceder. Si tu internet está encendido, el gestor solo obtiene precios hacia afuera, pero JAMÁS envía tu información. Todo se almacena localmente en la PC en `portfolio.db`.
* **No subir a internet tu Portfolio:** El archivo con tus finanzas es exclusivo, mantén su privacidad y, ante la duda, hace un respaldo regular del archivo `portfolio.db` ubicado en la carpeta principal.
