# 🎯 Traino.gg | Búnker de Gestión Modular para E-sports

**Traino** es una plataforma web centralizada diseñada para profesionalizar la organización interna de equipos competitivos de e-sports (con enfoque inicial en juegos tácticos como Rainbow Six Siege). Resuelve la dispersión de información, unificando agendas, tácticas y control de rendimiento en un solo entorno con accesos basados en roles.

---

## 🚀 Funcionalidades Principales

El sistema está dividido en tres ecosistemas aislados según el nivel de acceso:

*   👤 **Módulo Player:** Acceso ultra-rápido para fichaje de presentismo ("Punch-in/Punch-out"), visualización de agenda diaria y seguimiento de horas netas de práctica.
*   📋 **Módulo Coach:** Dashboard táctico de 24 horas. Permite agendar entrenamientos, asignar pools de mapas, gestionar el roster, controlar la asistencia del equipo en vivo y utilizar pizarras tácticas integradas (Miro).
*   ⚙️ **Módulo Admin:** Consola de infraestructura. Gestión de usuarios (CRUD), asignación de roles y control de la **Liga Global 2026** (ranking, logos y regiones de equipos rivales).

---

## 🛠️ Stack Tecnológico

*   **Backend:** Python 3 + Django
*   **Frontend:** HTML5, CSS3 (Custom Búnker UI), Bootstrap 5
*   **Base de Datos:** SQLite (Entorno de desarrollo) / Modelado ORM
*   **Autenticación:** Google Identity Services (OAuth2) + Django Auth
*   **Integraciones:** Iframes interactivos (Miro)

---

## ⚙️ Instrucciones de Instalación y Ejecución

Sigue estos pasos para desplegar el proyecto en un entorno de desarrollo local:

1. **Clonar o descargar el repositorio** e ingresar a la carpeta raíz del proyecto.
2. **Crear y activar el entorno virtual:**

       python -m venv traino_env
       traino_env\Scripts\activate

3. **Instalar las dependencias:**

       pip install django google-auth requests

4. **Aplicar las migraciones de la base de datos:**

       python manage.py migrate

5. **Levantar el servidor local (LEER NOTA IMPORTANTE):**

       python manage.py runserver localhost:8000

---

## ⚠️ NOTA TÉCNICA PARA EVALUADORES (Login de Google)

Para poder probar correctamente la integración del **Inicio de Sesión con Google**, es estrictamente necesario acceder a la plataforma mediante la URL con el alias local:

👉 **CORRECTO:** http://localhost:8000
❌ **INCORRECTO:** http://127.0.0.1:8000

**Justificación técnica:** Las políticas actuales de seguridad y CORS de la API de Google Identity Services bloquean la inyección del botón en entornos HTTP que utilicen direcciones IP directas (127.0.0.1) como medida antifraude. La única excepción permitida por Google para desarrollo local sin certificado SSL/HTTPS es el uso literal del dominio localhost.

---

## 🔮 Roadmap (Próximos Pasos)

*   [ ] **Módulo de Analítica Data Science:** Integración de la librería Pandas (Python) para procesar métricas de partidas (KDA, Winrate por mapa) y cruzarlas con el historial de asistencia.
*   [ ] **Gráficos Dinámicos:** Visualización de estadísticas mediante Chart.js.
*   [ ] **Responsive Avanzado:** Optimización de la matriz de agenda de 24 horas para pantallas móviles.

---

> **Desarrollado por:** Fernando Fernandez y Agustín.
> Proyecto académico para la carrera de Analista de Sistemas - Escuela Da Vinci (2026).