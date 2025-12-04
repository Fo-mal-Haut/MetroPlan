import Vue from 'vue'

// main.js
import uView from "uview-ui";
Vue.use(uView);


import App from './App'

// 如此配置即可
uni.$u.config.unit = 'rpx'

import './uni.promisify.adaptor'

Vue.config.productionTip = false

App.mpType = 'app'

const app = new Vue({
  ...App
})
app.$mount()
