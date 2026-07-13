module.exports = {
  apps: [
    {
      name: "Kumiho-Bot",
      script: "main.py",
      interpreter: "python3",
      watch: false,
      cwd: ".",
      env: {
        NODE_ENV: "development",
      }
    },
    {
      name: "Kumiho-API",
      script: "main.py",
      interpreter: "python3",
      watch: false,
      cwd: "./web/api",
      env: {
        NODE_ENV: "development",
      }
    },
    {
      name: "Kumiho-Dashboard",
      script: "./node_modules/vite/bin/vite.js",
      args: "--host 0.0.0.0",
      watch: false,
      cwd: "./web/dashboard",
      env: {
        NODE_ENV: "development",
      }
    }
  ]
};
