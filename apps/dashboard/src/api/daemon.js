import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const getDaemonStatus = () => client.get('/daemon/status')
export const getDaemonActivity = (lines = 50) => client.get('/daemon/activity', { params: { lines } })
export const startDaemon = () => client.post('/daemon/start')
export const stopDaemon = () => client.post('/daemon/stop')
export const restartDaemon = () => client.post('/daemon/restart')
export const getBoardData = () => client.get('/daemon/board')
export const syncMain = () => client.post('/daemon/sync-main')
export const getRuntimeStatus = () => client.get('/daemon/runtime-status')
