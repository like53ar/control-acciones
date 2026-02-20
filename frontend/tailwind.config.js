/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{html,ts}",
    ],
    theme: {
        extend: {
            colors: {
                zen: {
                    lightest: '#ffffff',
                    light: '#f7f9fa',
                    medium: '#e2e8f0',
                    dark: '#94a3b8',
                    darkest: '#334155',
                    text: '#0f172a',
                    accent: '#0ea5e9', // Un toque sutil de color si es necesario
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
