
<template>
  <div class="container mt-4">
    <h1 class="mb-4 text-center text-md-start">Datos de {{ formatTableName(tabla) }}</h1>

    <!-- Navegación entre tablas -->
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-4 shadow-sm">
      <div class="container-fluid">
        <span class="navbar-brand">Tablas</span>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li v-for="t in tablas" :key="t" class="nav-item">
              <router-link
                :to="`/${t}`"
                class="nav-link"
                :class="{ active: tabla === t }"
                @click="cargando = true"
              >
                {{ formatTableName(t) }}
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Filtro -->
    <div class="row mb-4">
      <div class="col-12 col-md-6 col-lg-4">
        <input
          v-model="filtro"
          class="form-control"
          placeholder="Filtrar por identificador exacto..."
          @input="aplicarFiltro"
        />
      </div>
    </div>

    <!-- Selector de columnas (Dropdown) -->
    <div class="dropdown mb-4">
      <button
        class="btn btn-outline-primary dropdown-toggle"
        type="button"
        id="columnasDropdown"
        data-bs-toggle="dropdown"
        aria-expanded="false"
      >
        Seleccionar Columnas ({{ columnasVisibles.length }} seleccionadas)
      </button>
      <ul class="dropdown-menu" aria-labelledby="columnasDropdown" style="max-height: 300px; overflow-y: auto;">
        <transition-group name="fade">
          <li v-for="columna in todasColumnas" :key="columna">
            <div class="dropdown-item">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  :value="columna"
                  v-model="columnasVisibles"
                  :id="`columna-${columna}`"
                  @change="actualizarColumnas"
                />
                <label class="form-check-label" :for="`columna-${columna}`">
                  {{ formatColumnName(columna) }}
                </label>
              </div>
            </div>
          </li>
        </transition-group>
      </ul>
    </div>

    <!-- Indicador de carga o error -->
    <div v-if="cargando" class="text-center my-4">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Cargando...</span>
      </div>
    </div>
    <div v-else-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
      {{ error }}
      <button type="button" class="btn-close" @click="error = null" aria-label="Close"></button>
    </div>

    <!-- Tabla de datos -->
    <div class="table-responsive">
      <transition-group tag="table" name="list" v-if="columnasVisibles.length > 0 && datos.length > 0" class="table table-striped table-bordered table-hover">
        <thead class="table-dark">
          <tr>
            <th v-for="columna in columnasVisibles" :key="columna">{{ formatColumnName(columna) }}</th>
            <th v-if="tabla === 'adjudicaciones' || tabla === 'modificados' || tabla === 'resultados_licitaciones'">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fila in datos" :key="fila.identificador">
            <td v-for="columna in columnasVisibles" :key="columna">
              <a v-if="columna === 'link_licitacion'" :href="fila[columna]" target="_blank" class="btn btn-link p-0">Enlace</a>
              <span v-else>{{ fila[columna] || '-' }}</span>
            </td>
            <td v-if="tabla === 'adjudicaciones' || tabla === 'modificados' || tabla === 'resultados_licitaciones'">
              <div class="d-flex flex-column flex-md-row gap-2">
                <button v-if="tabla === 'adjudicaciones'" class="btn btn-primary btn-sm" @click="verDetalleAdjudicacion(fila.identificador)">
                  Ver detalle adjudicación
                </button>
                <button v-if="tabla === 'modificados'" class="btn btn-primary btn-sm" @click="verDetalleModificados(fila.identificador)">
                  Ver detalle modificados
                </button>
                <button v-if="tabla === 'resultados_licitaciones'" class="btn btn-primary btn-sm" @click="verDetalleAdjudicacion(fila.identificador)">
                  Ver adjudicaciones
                </button>
                <button v-if="tabla === 'resultados_licitaciones'" class="btn btn-primary btn-sm" @click="verDetalleModificados(fila.identificador)">
                  Ver modificaciones
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </transition-group>
      <p v-else-if="!cargando" class="text-muted text-center mt-4">No hay datos disponibles.</p>
    </div>

    <!-- Paginación -->
    <div class="d-flex justify-content-center align-items-center mt-4">
      <nav>
        <ul class="pagination">
          <li class="page-item" :class="{ disabled: pagina === 1 || cargando }">
            <button class="page-link" @click="cambiarPagina(pagina - 1)">Anterior</button>
          </li>
          <li class="page-item disabled">
            <span class="page-link">Página {{ pagina }} de {{ totalPaginas }}</span>
          </li>
          <li class="page-item" :class="{ disabled: pagina === totalPaginas || cargando }">
            <button class="page-link" @click="cambiarPagina(pagina + 1)">Siguiente</button>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>

<script>
import { useDatosStore } from '../stores/datos';

export default {
  name: 'TablaDatos',
  props: {
    tabla: String,
  },
  setup() {
    const store = useDatosStore();
    return { store };
  },
  data() {
    return {
      cargando: false,
      error: null,
      columnasVisibles: [],
      todasColumnas: [],
    };
  },
  computed: {
    datos() {
      return this.store.datos;
    },
    columnas() {
      return this.store.columnas;
    },
    tablas() {
      return this.store.tablas;
    },
    pagina() {
      return this.store.pagina;
    },
    total() {
      return this.store.total;
    },
    totalPaginas() {
      return Math.ceil(this.total / this.store.limite);
    },
    filtro: {
      get() {
        return this.store.filtro;
      },
      set(value) {
        this.store.setFiltro(value);
      },
    },
  },
  watch: {
    async tabla(newTabla) {
      this.cargando = true;
      this.error = null;
      try {
        this.store.setPagina(1);
        await this.store.cargarDatos(newTabla);
        this.todasColumnas = this.columnas;
        this.actualizarColumnasVisibles();
      } catch (error) {
        this.error = 'Error al cargar los datos: ' + error.message;
      } finally {
        this.cargando = false;
      }
    },
    columnas(newColumnas) {
      this.todasColumnas = newColumnas;
      this.actualizarColumnasVisibles();
    },
  },
  async created() {
    this.cargando = true;
    this.error = null;
    try {
      await this.store.cargarTablas();
      await this.store.cargarDatos(this.tabla);
      this.todasColumnas = this.columnas;
      this.actualizarColumnasVisibles();
    } catch (error) {
      this.error = 'Error al cargar los datos: ' + error.message;
    } finally {
      this.cargando = false;
    }
  },
  methods: {
    actualizarColumnasVisibles() {
      if (this.tabla === 'resultados_licitaciones') {
        this.columnasVisibles = this.todasColumnas.filter(col => 
          col === 'estado' ||
          col === 'n_mero_de_expediente' ||
          col === '_rgano_de_contrataci_n' ||
          col === 'objeto_del_contrato' ||
          col === 'nif_oc' ||
          col === 'modificado'
        );
      } else {
        this.columnasVisibles = [...this.todasColumnas];
      }
      this.$forceUpdate();
    },
    async cambiarPagina(pagina) {
      this.cargando = true;
      this.error = null;
      try {
        this.store.setPagina(pagina);
        await this.store.cargarDatos(this.tabla);
      } catch (error) {
        this.error = 'Error al cargar los datos: ' + error.message;
      } finally {
        this.cargando = false;
      }
    },
    async aplicarFiltro() {
      this.cargando = true;
      this.error = null;
      try {
        await this.store.cargarDatos(this.tabla);
      } catch (error) {
        this.error = 'Error al cargar los datos: ' + error.message;
      } finally {
        this.cargando = false;
      }
    },
    actualizarColumnas() {
      this.$forceUpdate();
    },
    formatColumnName(name) {
      return name
        .replace(/___/g, ' - ')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
    },
    formatTableName(name) {
      return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
    },
    verDetalleAdjudicacion(identificador) {
      this.cargando = true;
      this.$router.push(`/detalle-adjudicacion/${identificador}`);
    },
    verDetalleModificados(identificador) {
      this.cargando = true;
      this.$router.push(`/detalle-modificados/${identificador}`);
    },
  },
};
</script>

<style scoped>
/* Animaciones existentes se mantienen */
</style>