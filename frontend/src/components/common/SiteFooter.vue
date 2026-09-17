<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <div class="footer-logo">
          <img :src="logo" alt="logo" />
          <span>党史学习智能问答系统</span>
        </div>
        <p class="footer-desc">
          以 Neo4j 知识图谱组织权威党史知识，提供可溯源、零编造的自然语言问答，
          配套图谱可视化、大事记时间轴、实体百科与知识测验，构成"问—学—练—测"闭环。
        </p>
        <div class="footer-stat">
          <span><b>{{ LABELS.length }}</b> 类实体</span>
          <span><b>{{ RELATIONS.length }}</b> 类关系</span>
          <span><b>{{ PERIODS.length }}</b> 个历史时期</span>
        </div>
      </div>

      <nav class="footer-nav" aria-label="功能导航">
        <h3>功能导航</h3>
        <router-link to="/qa">智能问答</router-link>
        <router-link to="/graph">知识图谱</router-link>
        <router-link to="/timeline">大事记时间轴</router-link>
        <router-link to="/quiz">知识测验</router-link>
      </nav>

      <nav class="footer-nav" aria-label="知识来源">
        <h3>知识来源</h3>
        <a v-for="s in SOURCES" :key="s.url" :href="s.url" target="_blank" rel="noopener">{{ s.name }}</a>
      </nav>

      <div class="footer-nav">
        <h3>使用说明</h3>
        <span class="footer-note">答案均由图谱事实经模板生成</span>
        <span class="footer-note">未收录问题回落权威原文段落</span>
        <span class="footer-note">每条知识均标注来源出处</span>
      </div>
    </div>

    <div class="footer-bottom">
      <span>全部知识来自权威公开出版物与官方网站 · 答案可溯源、零编造 · 仅供学习参考</span>
      <span class="footer-copy">© {{ year }} 基于知识图谱的党史学习智能问答系统 · 毕业设计作品</span>
    </div>
  </footer>
</template>

<script setup>
import logo from '@/assets/logo.svg'
import { LABELS, PERIODS, RELATIONS } from '@/utils/ontology'

// 规范页脚：品牌 + 规模数据 + 三组导航 + 版权条（开发规范 1.1「正规站点布局」）
const SOURCES = [
  { name: '中国共产党一百年大事记', url: 'https://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html' },
  { name: '党史百年·天天读', url: 'https://www.dswxyjy.org.cn/GB/434461/434470/434590/index.html' },
  { name: '《中国共产党简史》', url: 'https://www.idcpc.gov.cn/ztwy/tbtj/jdbnghlc/xxzl/jianshi/' },
  { name: '历次党代会数据库', url: 'https://www.12371.cn/special/lcddh/' },
]

const year = new Date().getFullYear()
// 页脚只展示本体常量（零接口依赖）：它在每个页面都渲染，若自行发请求，失败时会经 request
// 拦截器弹出全局「服务暂时不可用」提示——装饰性信息不应产生这种副作用。
// 实体总量等动态规模数据放在首页统计带展示。
</script>

<style scoped>
.site-footer {
  margin-top: 48px;
  /* 前台基调为庄重红 + 米白 + 金色强调（规范 1.1），页脚原先误用了后台的深蓝灰，
     此处改为深红棕渐变收口，与主视觉轮播的红色遮罩呼应 */
  background: linear-gradient(180deg, #5A1114 0%, #400C0F 55%, #300A0C 100%);
  color: rgba(255, 255, 255, 0.72);
  border-top: 3px solid var(--color-gold);
}
.footer-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 36px 20px 24px;
  display: grid;
  grid-template-columns: 2.2fr 1fr 1.3fr 1.3fr;
  gap: 32px;
}
.footer-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}
.footer-logo img {
  width: 28px;
  height: 28px;
}
.footer-desc {
  margin: 12px 0 14px;
  font-size: 13px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.68);
}
.footer-stat {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}
.footer-stat b {
  display: block;
  font-size: 18px;
  color: var(--color-gold);
  line-height: 1.5;
}
.footer-nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.footer-nav h3 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}
.footer-nav a {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);
  transition: color var(--transition);
}
.footer-nav a:hover {
  color: var(--color-gold);
}
.footer-note {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.72);
}
.footer-bottom {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 14px 20px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}
@media (max-width: 992px) {
  .footer-inner {
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }
}
</style>
