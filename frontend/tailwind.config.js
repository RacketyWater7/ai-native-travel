/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16213E",
        sand: "#F8F4EF",
        coral: "#FF5A5F"
      }
    }
  },
  plugins: []
};
