import './assets/main.css'
import { createApp } from 'vue';
import App from './App.vue';
// import VueToast from 'vue-toast-notification';
import ToastPlugin from 'vue-toast-notification';
import 'vue-toast-notification/dist/theme-sugar.css'; // 选择一个主题

const app = createApp(App)
app.use(ToastPlugin, { position: 'top' });

console.log('准备挂载应用到 #app');
app.mount('#app');
console.log('应用已挂载到 #app');
