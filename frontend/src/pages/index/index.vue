<template>
	<view class="container">
		<!-- 标题 -->
		<view class="header">
			<text class="title">MetroPlan - 城际铁路规划查询</text>
		</view>

		<!-- 输入区域 -->
		<view class="input-section">
			<!-- 起点站输入 -->
			<view class="input-group">
				<view class="label">起点站</view>
				<u-input 
					v-model="startStation" 
					placeholder="请输入起点站名称"
					clearable
					class="input-field"
				></u-input>
			</view>

			<!-- 终点站输入 -->
			<view class="input-group">
				<view class="label">终点站</view>
				<u-input 
					v-model="endStation" 
					placeholder="请输入终点站名称"
					clearable
					class="input-field"
				></u-input>
			</view>

			<!-- 查询按钮 -->
			<view class="button-group">
				<u-button 
					type="primary" 
					@click="queryPath"
					:loading="loading"
					class="search-button"
				>查询路径</u-button>
				<u-button 
					type="info" 
					@click="getStations"
					:loading="loadingStations"
					class="station-button"
				>获取车站列表</u-button>
			</view>
		</view>

		<!-- 输出区域 -->
		<view class="output-section">
			<!-- 错误提示 -->
			<u-toast ref="uToast"></u-toast>

			<!-- 结果显示 -->
			<view v-if="results.length > 0" class="results-container">
				<view class="result-header">
					<text class="result-title">查询结果 (共{{results.length}}条路径)</text>
				</view>
				
				<!-- 路径列表 -->
				<view v-for="(path, index) in results" :key="index" class="path-card">
					<view class="path-header">
						<view class="path-type">
							<u-tag 
								:text="path.type === 'Direct' ? '直达' : '换乘'" 
								:type="path.type === 'Direct' ? 'success' : 'warning'"
								size="mini"
							></u-tag>
						</view>
						<view class="path-time">
							<text class="time-text">{{path.departure_time}} → {{path.arrival_time}}</text>
						</view>
						<view class="path-duration">
							<text class="duration-text">{{path.total_time}}</text>
						</view>
					</view>

					<view class="path-details">
						<view class="detail-row">
							<text class="detail-label">列车序列:</text>
							<text class="detail-value">{{path.train_sequence.join(' → ')}}</text>
						</view>
						<view class="detail-row">
							<text class="detail-label">总耗时:</text>
							<text class="detail-value">{{path.total_minutes}}分钟</text>
						</view>
						<view class="detail-row">
							<text class="detail-label">换乘次数:</text>
							<text class="detail-value">{{path.transfer_count}}次</text>
						</view>
						<view v-if="path.is_fast" class="detail-row">
							<u-tag text="包含快速列车" type="primary" size="mini"></u-tag>
						</view>

						<!-- 换乘详情 -->
						<view v-if="path.transfer_details.length > 0" class="transfer-section">
							<text class="transfer-title">换乘详情:</text>
							<view v-for="(transfer, tIndex) in path.transfer_details" :key="tIndex" class="transfer-item">
								<text class="transfer-text">在 <text class="station-name">{{transfer.station}}</text> 换乘，到达 {{transfer.arrival_time}}，出发 {{transfer.departure_time}}，等待 {{transfer.wait_minutes}}分钟</text>
							</view>
						</view>
					</view>
				</view>
			</view>

			<!-- 车站列表显示 -->
			<view v-if="stationsList.length > 0" class="stations-container">
				<view class="stations-header">
					<text class="stations-title">可用车站 (共{{stationsList.length}}个)</text>
				</view>
				<view class="stations-grid">
					<view v-for="(station, index) in stationsList" :key="index" class="station-item">
						{{station}}
					</view>
				</view>
			</view>

			<!-- 空状态 -->
			<view v-if="results.length === 0 && stationsList.length === 0 && !loading && !loadingStations" class="empty-state">
				<text class="empty-icon">🔍</text>
				<text class="empty-text">输入起点站和终点站，点击"查询路径"获取结果</text>
			</view>
		</view>
	</view>
</template>

<script>
import { computePaths, listStations } from '@/algorithms/run_find_paths_demo';
	export default {
		data() {
			return {
				startStation: '',
				endStation: '',
				results: [],
				stationsList: [],
				loading: false,
				loadingStations: false,
				apiBaseUrl: 'http://localhost:5000'
			}
		},
		onLoad() {
			console.log('Page loaded')
		},
		methods: {
			// 查询路径 (使用前端本地算法替代后端 API)
			queryPath() {
				// 验证输入
				if (!this.startStation.trim()) {
					this.$refs.uToast.show({
						title: '请输入起点站',
						type: 'warning',
						duration: 2000
					})
					return
				}
				if (!this.endStation.trim()) {
					this.$refs.uToast.show({
						title: '请输入终点站',
						type: 'warning',
						duration: 2000
					})
					return
				}

				// 开始加载
				this.loading = true
				computePaths(this.startStation.trim(), this.endStation.trim(), 2, 90, false)
					.then((resp) => {
						this.loading = false
						const data = resp
						if (data.paths && data.paths.length > 0) {
							this.results = data.paths
							this.$refs.uToast.show({
								title: `找到${data.paths.length}条路径`,
								type: 'success',
								duration: 1000
							})
						} else {
							this.results = []
							this.$refs.uToast.show({
								title: '未找到路径',
								type: 'warning',
								duration: 2000
							})
						}
					})
					.catch((err) => {
						this.loading = false
						console.error('本地算法执行失败:', err)
						this.$refs.uToast.show({
							title: '路径查询出错（本地）',
							type: 'error',
							duration: 2000
						})
					})
			},

			// 获取车站列表 (从静态 JSON 提取)
			getStations() {
				this.loadingStations = true
				listStations()
					.then((arr) => {
						this.loadingStations = false
						this.stationsList = arr
						this.$refs.uToast.show({ title: `已加载${arr.length}个车站`, type: 'success', duration: 1000 })
					})
					.catch((err) => {
						this.loadingStations = false
						console.error('加载车站失败:', err)
						this.$refs.uToast.show({ title: '加载车站失败（本地）', type: 'error', duration: 2000 })
					})
			}
		}
	}
</script>

<style scoped lang="scss">
	.container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background-color: #f5f5f5;
	}

	.header {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		padding: 30rpx;
		text-align: center;
		color: white;
	}

	.title {
		font-size: 32rpx;
		font-weight: bold;
		color: white;
	}

	.input-section {
		padding: 30rpx;
		background-color: white;
		border-bottom: 1rpx solid #eee;
	}

	.input-group {
		margin-bottom: 20rpx;
	}

	.label {
		font-size: 28rpx;
		font-weight: bold;
		margin-bottom: 10rpx;
		color: #333;
	}

	.input-field {
		border-radius: 10rpx;
	}

	.button-group {
		display: flex;
		gap: 20rpx;
		margin-top: 20rpx;
	}

	.search-button {
		flex: 1;
	}

	.station-button {
		flex: 1;
	}

	.output-section {
		flex: 1;
		padding: 20rpx;
		overflow-y: auto;
	}

	.results-container,
	.stations-container {
		background-color: white;
		border-radius: 10rpx;
		padding: 20rpx;
		margin-bottom: 20rpx;
		box-shadow: 0 2rpx 10rpx rgba(0, 0, 0, 0.1);
	}

	.result-header,
	.stations-header {
		border-bottom: 2rpx solid #667eea;
		padding-bottom: 15rpx;
		margin-bottom: 15rpx;
	}

	.result-title,
	.stations-title {
		font-size: 28rpx;
		font-weight: bold;
		color: #333;
	}

	.path-card {
		padding: 15rpx;
		border-left: 4rpx solid #667eea;
		border-radius: 5rpx;
		background-color: #f9f9f9;
		margin-bottom: 15rpx;
		box-shadow: 0 1rpx 5rpx rgba(0, 0, 0, 0.05);
	}

	.path-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 15rpx;
		flex-wrap: wrap;
		gap: 10rpx;
	}

	.path-type {
		flex-shrink: 0;
	}

	.path-time {
		flex: 1;
		text-align: center;
	}

	.time-text {
		font-size: 28rpx;
		font-weight: bold;
		color: #333;
	}

	.path-duration {
		flex-shrink: 0;
		background-color: #667eea;
		color: white;
		padding: 8rpx 15rpx;
		border-radius: 20rpx;
	}

	.duration-text {
		font-size: 26rpx;
		color: white;
		font-weight: bold;
	}

	.path-details {
		background-color: white;
		padding: 15rpx;
		border-radius: 5rpx;
	}

	.detail-row {
		display: flex;
		margin-bottom: 10rpx;
		font-size: 26rpx;
		flex-wrap: wrap;
	}

	.detail-label {
		color: #666;
		margin-right: 10rpx;
		min-width: 80rpx;
		font-weight: bold;
	}

	.detail-value {
		color: #333;
		flex: 1;
		word-break: break-all;
	}

	.transfer-section {
		margin-top: 15rpx;
		padding-top: 15rpx;
		border-top: 1rpx solid #eee;
	}

	.transfer-title {
		font-size: 26rpx;
		font-weight: bold;
		color: #666;
		display: block;
		margin-bottom: 10rpx;
	}

	.transfer-item {
		background-color: #fff9e6;
		padding: 10rpx 15rpx;
		border-radius: 5rpx;
		margin-bottom: 8rpx;
		font-size: 24rpx;
		color: #333;
	}

	.transfer-text {
		color: #333;
	}

	.station-name {
		color: #764ba2;
		font-weight: bold;
	}

	.stations-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 10rpx;
	}

	.station-item {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		padding: 10rpx 20rpx;
		border-radius: 20rpx;
		font-size: 24rpx;
		text-align: center;
		flex-shrink: 0;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 60rpx 30rpx;
		text-align: center;
		color: #999;
	}

	.empty-icon {
		font-size: 80rpx;
		margin-bottom: 20rpx;
	}

	.empty-text {
		font-size: 28rpx;
		color: #999;
	}
</style>
