import { defineStore } from 'pinia';
import axios from 'axios';

export const useDatosStore = defineStore('datos', {
  state: () => ({
    tablas: [],
    datos: [],
    columnas: [],
    pagina: 1,
    limite: 5,
    total: 0,
    filtro: '',
  }),
  actions: {
    async cargarTablas() {
      try {
        const response = await axios.get('http://localhost:3000/api/tablas', { timeout: 5000 });
        this.tablas = response.data.tablas;
      } catch (error) {
        console.error('Error al cargar tablas:', error);
      }
    },
    async cargarModelResults() {
  try {
    const response = await axios.get('http://localhost:3000/api/model_results', { timeout: 5000 });
    this.modelResults = response.data;
  } catch (error) {
    console.error('Error al cargar resultados del modelo:', error);
  }
},
    async cargarDatos(tabla) {
      try {
        const response = await axios.get(`http://localhost:3000/api/${tabla}`, {
          params: { pagina: this.pagina, limite: this.limite, filtro: this.filtro },
          timeout: 5000,
        });
        this.datos = response.data.data;
        this.total = response.data.total;
        this.columnas = this.datos.length > 0 ? Object.keys(this.datos[0]) : [];
      } catch (error) {
        console.error(`Error al cargar datos de ${tabla}:`, error);
      }
    },
    setPagina(pagina) {
      this.pagina = pagina;
    },
    setFiltro(filtro) {
      this.filtro = filtro;
      this.pagina = 1;
    },
  },
});