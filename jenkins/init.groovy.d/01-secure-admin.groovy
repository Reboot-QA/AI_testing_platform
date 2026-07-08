try {
  def password = System.getenv('JENKINS_ADMIN_PASSWORD') ?: ''
  def username = System.getenv('JENKINS_ADMIN_USER') ?: 'admin'

  if (System.getenv('DISABLE_JENKINS_AUTH') == '1') {
    println '[secure-admin] DISABLE_JENKINS_AUTH=1，跳过'
    return
  }

  if (!password?.trim() || password == 'change-me-jenkins-password') {
    println '[secure-admin] JENKINS_ADMIN_PASSWORD 未配置，暂不启用登录'
    return
  }

  def jenkins = Jenkins.getInstance()
  if (jenkins.isUseSecurity()) {
    println '[secure-admin] 安全认证已启用，跳过'
    return
  }

  println '[secure-admin] 正在启用 Jenkins 本地账号登录...'

  def realm = new HudsonPrivateSecurityRealm(false)
  realm.createAccount(username, password)
  jenkins.setSecurityRealm(realm)

  def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
  strategy.setAllowAnonymousRead(false)
  jenkins.setAuthorizationStrategy(strategy)
  jenkins.save()

  println "[secure-admin] 已启用登录认证，用户名: ${username}"
} catch (Throwable t) {
  println "[secure-admin] 初始化失败（已忽略，不影响启动）: ${t.message}"
}
