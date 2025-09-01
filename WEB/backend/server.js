import express from 'express';
import sqlite3 from 'sqlite3';
import cors from 'cors';
import fs from 'fs';
import { promisify } from 'util';
import compression from 'compression';
import path from 'path';
import { fileURLToPath } from 'url';


// Obtener __dirname en ES Modules
const __filename = fileURLToPath(import.meta.url);




const app = express();
const port = 3000;

// Verificar si el archivo de la base de datos existe
const dbPath = path.resolve( '../../SQLite/licitacionesBD.db');
if (!fs.existsSync(dbPath)) {
  console.error(`El archivo de la base de datos no se encuentra en: ${dbPath}`);
  process.exit(1);
}

// Conectar a la base de datos SQLite
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error al conectar a la base de datos:', err.message);
    process.exit(1);
  }
  console.log('Conectado a la base de datos SQLite.');
});

// Promisificar db.all y db.get
const dbAll = promisify(db.all).bind(db);
const dbGet = promisify(db.get).bind(db);

// Listar tablas al iniciar
db.all("SELECT name FROM sqlite_master WHERE type='table'", [], (err, rows) => {
  if (err) {
    console.error('Error al listar tablas:', err.message);
  } else {
    console.log('Tablas en la base de datos:', rows.map(row => row.name));
  }
});

// Verificar índices
db.serialize(() => {
  db.run('CREATE INDEX IF NOT EXISTS idx_adjudicaciones_identificador ON adjudicaciones(identificador)');
  db.run('CREATE INDEX IF NOT EXISTS idx_criterios_adjudicacion_identificador ON criterios_adjudicacion(identificador)');
  db.run('CREATE INDEX IF NOT EXISTS idx_modificados_identificador ON modificados(identificador)');
  db.run('CREATE INDEX IF NOT EXISTS idx_resultados_licitaciones_identificador ON resultados_licitaciones(identificador)');
  db.run('CREATE INDEX IF NOT EXISTS idx_resultados_licitaciones_fecha_adjudicacion ON resultados_licitaciones(fecha_adjudicacion)');
  db.run('CREATE INDEX IF NOT EXISTS idx_modificados_fecha_modificacion ON modificados(fecha_de_modificacion)');
  console.log('Índices creados o verificados.');
});

// Middleware
app.use(compression());
app.use(cors());
app.use(express.json());

// Lista de tablas válidas
const tablasValidas = ['adjudicaciones', 'criterios_adjudicacion', 'modificados', 'resultados_licitaciones'];

// Función genérica para obtener datos
const obtenerDatosTabla = async (tabla, pagina, limite, filtro, res) => {
  try {
    if (!tablasValidas.includes(tabla)) {
      return res.status(400).json({ error: 'Tabla no válida' });
    }

    const startTime = Date.now();
    const offset = (pagina - 1) * limite;
    let query = `SELECT * FROM ${tabla}`;
    let params = [];

    if (filtro) {
      query += ` WHERE identificador = ?`;
      params.push(filtro);
    }

    query += ` ORDER BY identificador DESC LIMIT ? OFFSET ?`;
    params.push(limite, offset);

    const rows = await dbAll(query, params);
    const countQuery = filtro
      ? `SELECT COUNT(*) as total FROM ${tabla} WHERE identificador = ?`
      : `SELECT COUNT(*) as total FROM ${tabla}`;
    const result = await dbGet(countQuery, filtro ? [filtro] : []);
    console.log(`Consulta a ${tabla} completada en ${Date.now() - startTime}ms`);

    res.json({
      data: rows,
      total: result.total,
      pagina,
      limite
    });
  } catch (err) {
    console.error(`Error en consulta a ${tabla}:`, err.message);
    res.status(500).json({ error: err.message });
  }
};

// Endpoints
app.get('/api/adjudicaciones', async (req, res) => {
  const { pagina = 1, limite = 5, filtro = '' } = req.query;
  await obtenerDatosTabla('adjudicaciones', parseInt(pagina), parseInt(limite), filtro, res);
});

app.get('/api/criterios_adjudicacion', async (req, res) => {
  const { pagina = 1, limite = 5, filtro = '' } = req.query;
  await obtenerDatosTabla('criterios_adjudicacion', parseInt(pagina), parseInt(limite), filtro, res);
});

app.get('/api/modificados', async (req, res) => {
  const { pagina = 1, limite = 5, filtro = '' } = req.query;
  await obtenerDatosTabla('modificados', parseInt(pagina), parseInt(limite), filtro, res);
});

app.get('/api/resultados_licitaciones', async (req, res) => {
  const { pagina = 1, limite = 5, filtro = '' } = req.query;
  await obtenerDatosTabla('resultados_licitaciones', parseInt(pagina), parseInt(limite), filtro, res);
});

app.get('/api/tablas', async (req, res) => {
  try {
    const rows = await dbAll("SELECT name FROM sqlite_master WHERE type='table'", []);
    res.json({ tablas: rows.map(row => row.name).filter(name => tablasValidas.includes(name)) });
  } catch (err) {
    res.status(500).json({ error: 'Error al consultar la base de datos: ' + err.message });
  }
});

app.get('/api/test-db', async (req, res) => {
  try {
    const rows = await dbAll("SELECT name FROM sqlite_master WHERE type='table'", []);
    res.json({ tablas: rows.map(row => row.name) });
  } catch (err) {
    res.status(500).json({ error: 'Error al consultar la base de datos: ' + err.message });
  }
});
app.get('/api/model_results', (req, res) => {
  try {
    const results = JSON.parse(fs.readFileSync('E:/TFG/WEB/backend/model_results.json', 'utf8'));
    res.json(results);
  } catch (err) {
    console.error('Error al leer resultados del modelo:', err.message);
    res.status(500).json({ error: 'Error al cargar resultados del modelo' });
  }
});

// Iniciar el servidor
app.listen(port, () => {
  console.log(`Servidor corriendo en http://localhost:${port}`);
});

// Cerrar la conexión al apagar
process.on('SIGINT', () => {
  db.close((err) => {
    if (err) {
      console.error('Error al cerrar la base de datos:', err.message);
    } else {
      console.log('Conexión a la base de datos cerrada.');
    }
    process.exit(0);
  });
});