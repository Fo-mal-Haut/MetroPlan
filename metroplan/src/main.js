import Vue from 'vue'
import App from './App'
import './uni.promisify.adaptor'
import uView from "uview-ui";
Vue.use(uView);

import 'uview-ui/theme.scss'

Vue.config.productionTip = false

App.mpType = 'app'

const app = new Vue({
  ...App
})
app.$mount()

// 配置小程序分享
let mpShare = require('@/utils/mpShape.js');
Vue.mixin(mpShare)
