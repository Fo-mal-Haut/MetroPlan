# MetroPlan — 前端（metroplan）项目说明文档

## 一、概述

本项目前端位于 `metroplan` 目录，基于 uni-app（Vue 2 语法）开发，使用 `uview-ui` 作为组件库，可构建为 H5、各类小程序（微信/支付宝/百度 等）、以及 App（app-plus）。项目适合同时面向多端发布。

要点：
- 框架：uni-app（@dcloudio/uni-app）
- 视图库：Vue 2
- 状态管理：vuex
- HTTP：flyio
- UI：uview-ui

## 二、主要功能与目标

- 提供跨平台（H5 / 小程序 / App）展示与交互
- 使用 uni-app 的多端能力复用页面逻辑与样式
- 集成 uview-ui 提供基础样式与组件

## 三、项目结构（重要目录/文件）

- `package.json`：项目依赖与脚本（构建/开发/测试等）。
- `src/`：前端源码
  - `main.js`：应用入口，初始化 Vue、注册插件（如 uView）、全局 mixin 等
  - `App.vue`：应用根组件，包含生命周期钩子与全局样式
  - `pages/`：页面目录（每个页面通常含 template/script/style）
  - `utils/`：工具库（例如 `mpShape.js` 用于小程序分享配置）
  - `static/`：静态资源（logo、图片等）
- `public/index.html`：H5 构建的 HTML 模板
- `manifest.json`：uni-app 多端与打包配置（app、mp-weixin 等平台的专属字段）
- `vue.config.js`、`babel.config.js`、`postcss.config.js`：构建与转译相关配置
- `jsconfig.json`：路径别名配置（如 `@/* -> src/*`）
- `.docs/README.md`：当前说明文档（新建位置）

## 四、安装与本地运行（开发）

推荐使用 Yarn（项目 README 中建议），也可使用 npm。示例均在 PowerShell / Windows 下可用。

1) 安装依赖：

```powershell
# 推荐
yarn install
# 或者（使用 npm）
npm install
```

2) 启动 H5 开发服务器（热重载）：

```powershell
# 使用 yarn
yarn serve
# 或者直接运行 npm 脚本（等价于 yarn serve）
npm run serve
```

说明：`serve` 脚本会执行 `dev:h5`（uni-serve），在浏览器中以 H5 模式运行，便于快速调试页面与样式。

## 五、构建与发布

常用构建脚本在 `package.json` 中定义，支持多端目标：

- 打包 H5（生产）：

```powershell
yarn build
# 等价于
npm run build
# 直接指定 H5 平台（等同）
npm run build:h5
```

- 打包为 App（app-plus）：

```powershell
npm run build:app-plus
```

- 打包为小程序（以微信为例）：

```powershell
npm run build:mp-weixin
```

项目包含大量平台目标（例如 `build:mp-alipay`、`build:mp-baidu`、`build:mp-qq` 等），按需选择对应脚本。

## 六、常用脚本（摘自 package.json）

- `serve` -> 启动本地 H5 开发（调用 `dev:h5`）
- `build` -> 生产构建（默认 H5：调用 `build:h5`）
- `build:app-plus`、`build:mp-weixin`、`build:mp-alipay` 等 -> 针对指定平台构建
- `dev:...` 系列 -> 开发/热编译（带 --watch）
- `test:...` 系列 -> 使用 jest 运行测试（可为不同平台设置环境变量）

## 七、关键配置说明

- `manifest.json`：应用多端配置入口（应用 ID、版本、平台特有权限与设置）。
  - 在打包为 App 或小程序时会读取相应平台字段（例如 `mp-weixin`）。

- `vue.config.js`：项目级 webpack/构建快速设置，当前项目将 `uview-ui`、`z-paging` 设为需要转译的依赖（transpileDependencies）。

- `babel.config.js`：Babel 转译设置与按需引入配置，针对 uni-app 的运行平台调整 `useBuiltIns` 及插件集合。

- `jsconfig.json`：配置了 `@/*` 到 `src/*` 的路径别名，便于在代码中使用 `@/` 引用源文件。

- `postcss.config.js`：处理 CSS 导入、自动前缀等（H5 平台会开启不同选项）。

## 八、调试与注意事项

- Node 与包管理器：建议使用 Node.js 的 LTS 版本（12/14/16 等任一受支持 LTS）；建议使用 Yarn 保持与项目 README 的一致性。
- 环境变量：脚本中使用 `cross-env` 设置 `UNI_PLATFORM`、`NODE_ENV` 等，确保 `cross-env` 已安装（在 devDependencies 中）。
- H5 下调试：运行 `yarn serve` 后在浏览器打开提供的本地地址进行调试。
- 小程序调试：构建小程序后，按平台（微信/支付宝等）使用对应小程序开发者工具加载生成的代码进行调试。
- App（app-plus）打包：一般需配合 HBuilderX 或云打包服务（依赖本地环境与证书配置）。

## 九、测试

项目集成了 jest 相关脚本：`test:h5`、`test:android`、`test:ios` 等，可使用：

```powershell
npm run test:h5
# 或
yarn test:h5
```

注意：Jest 的运行依赖项目中配置的环境变量（如 UNI_PLATFORM）；在 Windows 下使用 cross-env 会更稳定。

## 十、常见问题与快速排查

- 启动时报错找不到模块：请先执行 `yarn install`（或 `npm install`），确保 node_modules 已正确安装。
- 构建时报错与平台相关：确认执行的 `UNI_PLATFORM` 值是否正确以及对应的插件/SDK 是否配置（例如小程序的 appid）。
- 样式丢失或组件异常：确认是否正确引入 `uview-ui/index.scss`（项目在 `App.vue` 中以全局方式引入），并检查 `transpileDependencies` 是否包含第三方 ES6 代码需要转译的库（例如 uview）。

## 十一、维护与贡献建议

- 在修改 UI 组件或样式前，先在 H5 模式下用 `yarn serve` 验证视觉效果，再进行平台特有适配。
- 若新增第三方库并出现兼容问题，请在 `vue.config.js` 或 `babel.config.js` 中配置转译规则，或将该库添加到 `transpileDependencies`。
- 添加或修改页面时，遵循 `src/pages` 的页面结构规范（页面配置由 uni-app 的 pages.json 控制，注意保持路由一致性）。

## 十二、文档位置与交付

本说明已保存为：

- `metroplan/.docs/README.md`（当前文件）

请在需要时将该文件补充更多使用示例、页面路由说明、组件库使用约定或截图等。

---

如需我把文档扩展为：
- 详细的页面路由（从 pages.json 汇总）
- 常见修改场景的示例（新增页面/接入 API/打包发布到微信）

我可以继续自动生成并补充到 `.docs` 中。