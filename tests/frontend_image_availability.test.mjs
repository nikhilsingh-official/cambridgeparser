import assert from 'node:assert/strict'
import test from 'node:test'

import {
  imageIsAvailable,
  rememberUnavailableImage,
} from '../src/website/frontend/src/services/imageAvailability.js'

test('a failed optional question image is marked unavailable', () => {
  const unavailableImages = new Set()
  const image = { src: 'images/q_42.png' }

  assert.equal(imageIsAvailable(image, unavailableImages), true)

  rememberUnavailableImage(unavailableImages, image)

  assert.equal(imageIsAvailable(image, unavailableImages), false)
  assert.equal(imageIsAvailable(null, unavailableImages), false)
})
