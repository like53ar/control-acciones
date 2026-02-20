/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{html,ts}",
    ],
    theme: {
        extend: {
            colors: {
                zen: {
                    lightest: '#1e293b', // Fondo de formularios y tarjetas elevadas
                    light: '#0f172a',    // Fondo principal de la página
                    medium: '#334155',   // Bordes y separadores divisorios
                    dark: '#94a3b8',     // Texto secundario o leyendas
                    darkest: '#f8fafc',  // Títulos blancos, fuertes
                    text: '#cbd5e1',     // Texto regular base
                    accent: '#38bdf8',   // Acentos azules
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
