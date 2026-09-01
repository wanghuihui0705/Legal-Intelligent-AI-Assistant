import Vue from 'vue'
import Router from 'vue-router'

Vue.use(Router)

export default new Router({
  //加上history后,路径就不会显示#了
  mode:'history',
  routes: [
    // Login.vue 路由
    {
      // 访问路由 --- 需要拼接在客户端的协议、IP、端口号后面构成完整请求路径
      path: '/',
      //⭐ 设置拦截属性meta
      meta: {
        isLogin: false, // 不拦截
      },
      // 通过path属性的路径访问到的页面
      component: () => import('@/views/Login.vue')
    },
    // chat.vue 路由
    {
      // 访问路由 --- 需要拼接在客户端的协议、IP、端口号后面构成完整请求路径
      path: '/goChat',
      //⭐ 设置这个路由访问需要拦截
      meta: {
        isLogin: true, // 有登录拦截
      },
      // 通过path属性的路径访问到的页面
      component: () => import('@/views/Chat.vue')
    },
  ]
})
