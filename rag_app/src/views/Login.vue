<template>
  <div class="login-container">
    <div class="login-card">
      <!-- 标题区域 -->
      <div class="login-header">
        <h2>欢迎登录</h2>
        <p>Welcome Back</p>
      </div>

      <!-- 表单区域：使用 el-form 替代原生 form -->
      <el-form
        :model="user"
        ref="loginForm"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="user.username"
            placeholder="请输入账号"
            prefix-icon="el-icon-user"
            size="large"
          ></el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="user.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="el-icon-lock"
            size="large"
            show-password
            @keyup.enter.native="login"
          ></el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            @click="login"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
//相当于之前的创建Vue对象
export default {
  name: "Login",
  data() {
    return {
      user: {
        username: 'wyh',
        password: '123456',
      },
    }
  },
  methods: {
    login() {
      // ✅ 原有逻辑完全保留
      this.$axios({
        url: this.$serverUrlBase + 'users/login',
        method: 'post',
        data: JSON.stringify(this.user),
      }).then(res => {
        if (res.data.code === 200) {
          // 给用户看的提示信息
          this.$message.success(res.data.msg);
          // 登录成功把当前用户名存起来
          sessionStorage.setItem('username', this.user.username);
          // 把唯一标识存起来
          sessionStorage.setItem('userId',res.data.data)
          // 添加一个延迟函数 --- 等待几秒后执行内部的内容
          setTimeout(() => {
            // 跳转到聊天页面 --- chat.vue，实际上就是切换路由显示
            this.$router.push("/goChat"); // push方法参数：配置路由的path属性值
          }, 1000); // 等1000ms后执行handler参数内容

        } else {
          this.$message.error(res.data.msg);
        }

      })
    }
  },
  mounted() {

  },
}
</script>

<style scoped>
/* 全屏居中容器 + 渐变背景 */
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 卡片样式 */
.login-card {
  width: 420px;
  padding: 40px 36px 30px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

/* 标题样式 */
.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 6px;
  font-weight: 700;
}

.login-header p {
  font-size: 14px;
  color: #909399;
  letter-spacing: 2px;
}

/* 输入框圆角优化 */
.login-form ::v-deep .el-input__inner {
  border-radius: 8px;
  height: 44px;
  line-height: 44px;
}

/* 登录按钮全宽 + 圆角 */
.login-btn {
  width: 100%;
  border-radius: 8px;
  font-size: 16px;
  letter-spacing: 6px;
  margin-top: 8px;
}
</style>
