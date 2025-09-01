
<template>
  <div class="container mt-4">
    <h1 class="mb-4 text-center text-md-start">Detalle de Modificados: {{ identificador }}</h1>

    <div v-if="cargando" class="text-center my-4">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Cargando...</span>
      </div>
    </div>
    <div v-else-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
      {{ error }}
      <button type="button" class="btn-close" @click="error = null" aria-label="Close"></button>
    </div>
    <div v-else-if="modificados.length > 0">
      <transition-group name="list">
        <div v-for="(mod, index) in modificados" :key="index" class="card shadow-sm mb-3">
          <div class="card-header bg-light">
            <h3 class="h5 mb-0">Modificación {{ index + 1 }}</h3>
          </div>
          <div class="card-body">
            <ul class="list-group list-group-flush">
              <li v-for="(value, key) in mod" :key="key" class="list-group-item">
                <strong>{{ formatColumnName(key) }}:</strong>
                <a v-if="key === 'link_licitacion'" :href="value" target="_blank" class="btn btn-link p-0">Enlace</a>
                <span v-else>{{ value || '-' }}</span>
              </li>
            </ul>
          </div>
        </div>
      </transition-group>
      <button class="btn btn-outline-secondary mt-3" @click="volver">Volver</button>
    </div>
    <p v-else class="text-muted mt-4 text-center">No se encontraron modificados para este identificador.</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DetalleModificados',
  data() {
    return {
      identificador: this.$route.params.id,
      modificados: [],
      cargando: false,
      error: null,
    };
  },
  async created() {
    this.cargando = true;
    try {
      const response = await axios.get(`http://localhost:3000/api/modificados?filtro=${this.identificador}`);
      this.modificados = response.data.data;
    } catch (error) {
      this.error = 'Error al cargar los modificados: ' + error.message;
    } finally {
      this.cargando = false;
    }
  },
  methods: {
    formatColumnName(name) {
      return name
        .replace(/___/g, ' - ')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
    },
    volver() {
      this.$router.go(-1);
    },
  },
};
</script>

<style scoped>
/* Estilos existentes se mantienen, similares a DetalleCriterios */
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.card {
  border-radius: 8px;
  transition: transform 0.2s ease;
}
.card:hover {
  transform: translateY(-2px);
}

.list-group-item {
  padding: 12px 16px;
}

.btn {
  transition: all 0.2s ease;
}
</style>