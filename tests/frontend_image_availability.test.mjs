import assert from 'node:assert/strict'
import test from 'node:test'

import {
  imageIsAvailable,
  rememberUnavailableImage,
// path updated - the IDE's services moved to src/lib/ide/ when the two
// apps merged into one.
} from '../src/lib/ide/imageAvailability.js'

test('a failed optional question image is marked unavailable', () => {
  const unavailableImages = new Set()
  const image = { src: 'images/q_42.png' }

  assert.equal(imageIsAvailable(image, unavailableImages), true)

  rememberUnavailableImage(unavailableImages, image)

  assert.equal(imageIsAvailable(image, unavailableImages), false)
  assert.equal(imageIsAvailable(null, unavailableImages), false)
})
