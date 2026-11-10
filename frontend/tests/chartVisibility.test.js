import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createRenderer, h, nextTick, ref } from 'vue'
import { useChartVisibility } from '../src/composables/useChartVisibility.js'

// Exercise component mount/update/unmount without requiring a browser DOM.
const renderer = createRenderer({
  createElement: type => ({ type, children: [] }),
  createText: text => ({ text }),
  createComment: text => ({ text }),
  setText: (node, text) => { node.text = text },
  setElementText: (node, text) => { node.text = text },
  patchProp: () => {},
  insert(node, parent) { parent.children.push(node); node.parent = parent },
  remove(node) { node.parent.children = node.parent.children.filter(child => child !== node) },
  parentNode: node => node.parent,
  nextSibling: () => null,
})

function mountChart() {
  const data = ref('initial')
  let mounts = 0
  let chartProps
  const Chart = {
    props: ['data'],
    setup(props) {
      mounts++
      chartProps = props
      return () => h('span', props.data)
    },
  }
  const app = renderer.createApp({
    setup() {
      const target = ref(null)
      const ready = useChartVisibility(target)
      return () => h('div', { ref: target }, ready.value ? [h(Chart, { data: data.value })] : [])
    },
  })
  app.mount({ children: [] })
  return { app, data, mounts: () => mounts, chartData: () => chartProps?.data }
}

test('offscreen charts defer mounting, use fresh data and retain state after leaving the viewport', async () => {
  const original = globalThis.IntersectionObserver
  let notify
  let observed
  let disconnects = 0
  globalThis.IntersectionObserver = class {
    constructor(callback, options) {
      notify = callback
      assert.equal(options.rootMargin, '200px 0px')
    }
    observe(target) { observed = target }
    disconnect() { disconnects++ }
  }
  let chart
  try {
    chart = mountChart()
    assert.equal(observed.type, 'div')
    assert.equal(chart.mounts(), 0)
    notify([{ isIntersecting: false }])
    chart.data.value = 'updated before visibility'
    await nextTick()
    assert.equal(chart.mounts(), 0)

    notify([{ isIntersecting: true }])
    await nextTick()
    assert.equal(chart.mounts(), 1)
    assert.equal(chart.chartData(), 'updated before visibility')
    assert.equal(disconnects, 1)

    notify([{ isIntersecting: false }])
    chart.data.value = 'regenerated'
    await nextTick()
    assert.equal(chart.mounts(), 1)
    assert.equal(chart.chartData(), 'regenerated')
    chart.app.unmount()
    chart = undefined
    assert.equal(disconnects, 2)
  } finally {
    chart?.app.unmount()
    globalThis.IntersectionObserver = original
  }
})

test('unmounting an unseen chart disconnects the observer', () => {
  const original = globalThis.IntersectionObserver
  let disconnected = false
  globalThis.IntersectionObserver = class {
    observe() {}
    disconnect() { disconnected = true }
  }
  try {
    const chart = mountChart()
    assert.equal(chart.mounts(), 0)
    chart.app.unmount()
    assert.equal(disconnected, true)
  } finally {
    globalThis.IntersectionObserver = original
  }
})

test('browsers without IntersectionObserver still mount charts', async () => {
  const original = globalThis.IntersectionObserver
  globalThis.IntersectionObserver = undefined
  let chart
  try {
    chart = mountChart()
    await nextTick()
    assert.equal(chart.mounts(), 1)
    assert.equal(chart.chartData(), 'initial')
  } finally {
    chart?.app.unmount()
    globalThis.IntersectionObserver = original
  }
})
