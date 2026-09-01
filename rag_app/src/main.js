// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import router from './router'
Vue.config.productionTip = false

//1.引入element-ui(官网里面写了引入的代码)
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
Vue.use(ElementUI);

// 2.引入axios.js
import axios from 'axios'
// 设置post请求数据格式
axios.defaults.headers.post['Content-Type'] = 'application/json'
// 设置put请求数据格式
axios.defaults.headers.put['Content-Type'] = 'application/json'
// 设置全局 axios 写法,（后续使用时:this.$axios）
Vue.prototype.$axios = axios

//3.配置服务器的请求路径公共部分(后续使用时:this.$serverUrlBase)
Vue.prototype.$serverUrlBase='http://localhost:8000/'

//4.引入markdown解析
// ========== Markdown ==========
import marked from 'marked'
import DOMPurify from 'dompurify'
// marked 基础配置
marked.setOptions({
breaks: true, // 支持换行
gfm: true, // GitHub 风格
smartLists: true,
smartypants: false
})
function normalizeMarkdown(text) {
return text
.replace(/(#{1,6} )/g, '\n$1')
.replace(/- /g, '\n- ')
}
// 全局 markdown 渲染方法
Vue.prototype.$renderMarkdown = function (text) {
if (!text) return ''
const rawHtml = marked(normalizeMarkdown(text))
return DOMPurify.sanitize(rawHtml)
}

// 导航钩子 --- 未登录拦截
// to：去哪里
// from：从哪里来
// next：放行
router.beforeEach((to, from, next) => {
   // 取出登录用户名
   let username = sessionStorage.getItem('username');
   // 判断是否需要拦截
   if (to.meta.isLogin) {
     // 需要拦截 --- 判断是否登录了，登录了则放行，否则拦截
     if (username) {
       next();
     } else {
       // 提示信息,自动回到登录页面
       alert('请先登录!');
       next('/');
     }
   } else {
     // 不拦截 --- 放行
     next();
   }
});



/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})
