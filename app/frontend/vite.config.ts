import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// 开发环境静态文件服务中间件
function serveDataPlugin() {
  return {
    name: 'serve-data',
    configureServer(server: any) {
      // 项目根目录的 data 文件夹
      const dataDir = path.resolve(__dirname, '../../data')
      
      server.middlewares.use('/data', (req: any, res: any, next: any) => {
        const filePath = path.join(dataDir, req.url || '')
        
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const ext = path.extname(filePath)
          const contentType = ext === '.json' ? 'application/json' 
            : ext === '.jsonl' ? 'application/x-ndjson' 
            : 'text/plain'
          
          res.setHeader('Content-Type', `${contentType}; charset=utf-8`)
          fs.createReadStream(filePath).pipe(res)
        } else {
          next()
        }
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), serveDataPlugin()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
