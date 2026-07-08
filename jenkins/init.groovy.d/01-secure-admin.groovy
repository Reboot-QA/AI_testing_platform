import jenkins.model.Jenkins
import hudson.security.*

def password = System.getenv('JENKINS_ADMIN_PASSWORD') ?: ''
def username = System.getenv('JENKINS_ADMIN_USER') ?: 'admin'

if (!password?.trim() || password == 'change-me-jenkins-password') {
  println '[secure-admin] JENKINS_ADMIN_PASSWORD 未配置，暂不启用登录（请配置 jenkins/.env 后重启）'
  return
}

def jenkins = Jenkins.getInstance()
if (jenkins.isUseSecurity()) {
  println '[secure-admin] 安全认证已启用，跳过'
  return
}

println '[secure-admin] 正在启用 Jenkins 本地账号登录...'

def realm = new HudsonPrivateSecurityRealm(false)
try {
  realm.createAccount(username, password)
} catch (Exception e) {
  println "[secure-admin] 创建用户失败: ${e.message}"
  return
}

jenkins.setSecurityRealm(realm)

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
jenkins.setAuthorizationStrategy(strategy)
jenkins.save()

println "[secure-admin] 已启用登录认证，用户名: ${username}"
