# 🧘‍♂️ Portafolio Zen - Control de Inversiones

Sistema de control y gestión de inversiones (Acciones y Cedears). Evolucionado desde un script básico hacia una **aplicación web moderna, asíncrona y de pila completa (Full-Stack)** diseñada de manera exclusiva para uso privado.

## 🚀 Arquitectura y Tecnologías
Esta plataforma abandonó su dependencia en Python a favor de un ecosistema **100% JavaScript / TypeScript**, asegurando velocidad, estabilidad web y evitando cruces de procesos.

*   **Backend Minimalista (Node.js)**: Utiliza `Express` para el ruteo, `SQLite3` para la persistencia de datos local, `yahoo-finance2` para el autocompletado de empresas y consultas a APIs públicas de mercado.
*   **Frontend Unificado (Angular)**: Single Page Application (SPA) que elimina la necesidad de recargas de pantalla (cero parpadeos o renderizados forzados).  
*   **Estética (Tailwind CSS)**: Interfaz de usuario "Zen Dark", diseñada con colores marinos Premium, animaciones fluidas, flexbox asimétrico y tipografía limpia.

## ✨ Funcionalidades Clave

*   **Cinta de Cotizaciones Continua (Ticker Tape)**: Un robusto *Ticker Tape* integrado en el encabezado de la aplicación que muestra en tiempo real las variaciones de mercado.
    *   **Acciones Top Globales**: Seguimiento del S&P 500, Nasdaq 100 y Dow Jones junto con más de 50 de las principales empresas del mundo (Apple, Nvidia, Microsoft, Tesla, etc.).
    *   **Criptomonedas**: Monitoreo en vivo de BTC, ETH, SOL, XRP y ADA mediante Binance.
    *   **Materias Primas (Commodities)**: Futuros agrícolas en tiempo real conectados a CBOT e ICE (Soja, Trigo, Maíz, Café, Cacao, Azúcar y Jugo de Naranja) junto al Oro, Plata y Petróleo.
    *   **Mercado Forex (Divisas)**: Seguimiento de cruces locales e internacionales (USD/MXN, USD/BRL, EUR/TRY, etc.).
*   **Layout Adaptativo**: Disposición dividida que permite visualizar, en una sola pantalla, el formulario de carga interactiva, tarjetas de ganancia global, tabla histórica y resúmenes laterales.
*   **Autocompletado Inteligente**: Al escribir el Ticker (Código) de la acción, el backend Node se comunica con Yahoo Finance para precargar el nombre oficial de la empresa y bloquear errores tipográficos.
*   **Historial de Ventas**: Sistema robusto de persistencia que diferencia entre eliminar un registro falso por error y registrar la "Venta Real" de un activo (cambio de status de OPEN a CLOSED guardando precio y fecha de salida).
*   **Oráculo Cripto (Binance)**: Conector en tiempo real al servidor de Binance para mostrar la conversión dinámica del par **USDT/ARS** (Dólar Cripto).
*   **Resumen Consolidado**: Cuadro lateral que agrupa matemáticamente las inversiones (Ej. múltiples compras de una misma empresa convergen en un monto de capital único valorizado).

## 🔒 Privacidad y Seguridad
La aplicación corre íntegramente en `localhost`. La base de datos financiera central (`portfolio.db`) está auditada mediante políticas estrictas de `.gitignore`. **Los datos de inversión nunca escapan hacia GitHub ni la nube pública**.

## 🛠️ Instalación y Uso Local
Este software corre mediante un ejecutador maestro para ecosistemas Windows.
1. Clonar el repositorio.
2. Hacer doble clic sobre `launcher.vbs`.
3. El lanzador matará instancias conflictivas anteriores, silenciará las consolas de Node/Angular, levantará una "Splash Screen" (pantalla de carga de alta gama escrita en HTA firmada por el autor), y abrirá el navegador automático en `http://localhost:4200`.

---
*Desarrollado y refinado para la máxima concentración financiera por Fabian A.Correa*
