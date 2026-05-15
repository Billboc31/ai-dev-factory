import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const getDaemonStatus = () => client.get('/daemon/status')
export const startDaemon = () => client.post('/daemon/start')
export const stopDaemon = () => client.post('/daemon/stop')
export const restartDaemon = () => client.post('/daemon/restart')
