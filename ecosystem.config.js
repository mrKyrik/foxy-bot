module.exports = {
  apps: [
    {
      name: "Kumiho-Bot",
      script: "main.py",
      interpreter: "python",
      watch: false,
      cwd: ".",
      env: {
        NODE_ENV: "development",
      }
    },
    {
      name: "Kumiho-API",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 3001",
      interpreter: "python",
      watch: false,
      cwd: "./web/api",
      env: {
        NODE_ENV: "development",
      }
    },
    {
      name: "Kumiho-Dashboard",
      script: "./node_modules/vite/bin/vite.js",
      watch: false,
      cwd: "./web/dashboard",
      env: {
        NODE_ENV: "development",
      }
    }
  ]
};
