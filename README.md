# 🧘‍♂️ Portafolio Zen - Control de Inversiones

Sistema completo de gestión de inversiones personales con captura automática de históricos de precios. Aplicación web Full-Stack diseñada para uso privado local.

## 🎯 ¿Qué es Portafolio Zen?
Plataforma que centraliza el control de tus inversiones en acciones y CEDEARs, con seguimiento en tiempo real de mercados globales y construcción automática de históricos para análisis de tendencias.

### Características Principales
* **Portfolio Inteligente**: Registro y seguimiento de todas tus posiciones (compras, ventas, ganancias/pérdidas)
* **Histórico Automático**: Captura diaria de precios al cierre del mercado para análisis temporal
* **Ticker Tape Global**: Seguimiento continuo de S&P 500, Nasdaq, Dow Jones, 50+ acciones top, criptomonedas, commodities y forex
* **Autocompletado Yahoo Finance**: Validación automática de símbolos y nombres de empresas
* **Oráculo Cripto**: Conversión USDT/ARS en tiempo real vía Binance
* **100% Privado**: Todo corre en localhost, sin cloud, sin telemetría

## 🏗️ Tecnologías
Arquitectura Full-Stack JavaScript/TypeScript

* **Backend**: Node.js + Express + SQLite3
* **Frontend**: Angular + Tailwind CSS
* **Datos**: Yahoo Finance API + Binance API
* **Automatización**: Scheduler para capturas programadas

## ✨ Sistema de Históricos (Nuevo)
### Captura Automática de Precios
El sistema registra automáticamente el precio de cierre de todos tus activos activos cada día a las 17:00 EST (21:00 ARG), construyendo una base de datos temporal que permite:

* **Análisis de Performance**: Evolución de cada activo en períodos personalizados (30/60/90 días)
* **Detección de Tendencias**: Identificar patrones alcistas o bajistas
* **Backtesting**: Simular estrategias de inversión con datos reales
* **Reportes Fiscales**: Consultar precio exacto en cualquier fecha pasada
* **Alertas Inteligentes**: Configurar notificaciones cuando un activo retorna a niveles históricos

### Captura Manual
Además del registro automático, incluye un botón "Precios Finales" que permite capturar instantáneas del mercado en cualquier momento.

### Ventana de Auditoría
Modal emergente que muestra todo el historial de un activo específico ordenado por fecha, con precio y variación porcentual del día.

## 🔍 Funcionalidades del Portfolio
### Gestión de Posiciones
* Registro de compras con fecha, precio y cantidad
* Actualización de precios en tiempo real
* Sistema de ventas que diferencia entre "eliminar error" y "registrar venta real"
* Conservación del histórico de posiciones cerradas

### Ticker Tape Continuo
Cinta superior con cotizaciones en tiempo real de:
* **Índices**: S&P 500, Nasdaq 100, Dow Jones
* **Acciones Top**: Apple, Microsoft, Nvidia, Tesla, Amazon, Google, Meta...
* **Criptomonedas**: Bitcoin, Ethereum, Solana, Ripple, Cardano
* **Commodities**: Oro, Plata, Petróleo, Soja, Trigo, Maíz, Café, Cacao
* **Forex**: USD/MXN, USD/BRL, EUR/TRY y otros cruces relevantes

### Resumen Consolidado
Panel que agrupa matemáticamente múltiples compras del mismo activo en una valorización única, mostrando capital invertido vs valor actual.

## 🔒 Privacidad y Seguridad
* **Localhost Only**: La aplicación solo es accesible desde tu computadora
* **Base de Datos Local**: SQLite almacenado en tu disco, nunca en la nube
* **Git Protegido**: Políticas estrictas que evitan versionar datos financieros
* **Zero Telemetría**: Sin analytics, sin tracking externo
* **APIs Públicas**: Solo consulta precios de mercado, nunca envía tus posiciones

## 🚀 Instalación
### Requisitos
* Node.js versión 18 o superior
* Sistema operativo Windows 10/11
* Navegador moderno (Chrome, Edge, Firefox)

### Inicio Rápido
1. Clonar repositorio
2. Hacer doble clic en `launcher.vbs`
3. El sistema se abre automáticamente en `http://localhost:4200`

### ¿Qué hace el Launcher?
Script maestro que ejecuta toda la infraestructura en un solo clic:
* Elimina procesos anteriores para evitar conflictos
* Levanta el backend (puerto 3000)
* Levanta el frontend (puerto 4200)
* Muestra splash screen de carga
* Abre el navegador automáticamente

## 📊 API REST
### Endpoints de Portfolio
* Listar posiciones activas y cerradas
* Crear nueva posición
* Actualizar cantidad o precio
* Eliminar posición
* Registrar venta con fecha y precio de salida
* Autocompletar símbolos desde Yahoo Finance

### Endpoints de Históricos
* Obtener histórico completo de un activo
* Obtener último precio registrado
* Consultar rango de fechas específico
* Histórico de todo el portfolio
* Captura manual de snapshot
* Estadísticas (mínimo, máximo, promedio)

## 🛣️ Roadmap
### ✅ Versión Actual (1.0)
* Portfolio con CRUD completo
* Ticker Tape multi-mercado
* Sistema de ventas con histórico
* Captura de precios manuales
* Base de datos de históricos
* Launcher automático

### 🚧 Próximamente (1.1)
* Gráficos interactivos de evolución de precios
* Exportación de históricos a Excel/CSV
* Automatización completa del scheduler diario
* Comparador de rendimientos entre activos

### 🔮 Futuro (2.0)
* Alertas por precio objetivo
* Análisis técnico básico (medias móviles, RSI, MACD)
* Soporte multi-portfolio
* Dashboard de performance con métricas avanzadas

## 🐛 Solución de Problemas
### El launcher no arranca
* Verificar que Node.js esté instalado correctamente
* Comprobar que los puertos 3000 y 4200 estén libres
* Ejecutar como administrador si hay restricciones de permisos

### Error de base de datos
* La aplicación crea automáticamente las tablas necesarias en el primer arranque
* Si hay inconsistencias, el sistema detecta esquemas antiguos y los migra

### Símbolos no encontrados
* Algunos activos requieren sufijos especiales (ej: `BRK-B` para Berkshire Hathaway)
* Los índices llevan prefijo `^` (ej: `^GSPC` para S&P 500)

## 📁 Estructura del Proyecto
```text
portafolio-zen/
├── backend/          # Servidor Node.js + API REST
├── frontend/         # Aplicación Angular
├── tools/            # Scripts de utilidad
├── portfolio.db      # Base de datos (no versionada)
├── launcher.vbs      # Lanzador maestro
└── splash.hta        # Pantalla de carga
```

## 📝 Notas Finales
**Uso Personal Exclusivo** - Proyecto desarrollado para gestión privada de patrimonio.
*Desarrollado por Fabian A. Correa*
