import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

if (!navigator.clipboard) {
	Object.defineProperty(navigator, 'clipboard', {
		value: {
			writeText: async () => undefined,
		},
		configurable: true,
	})
}

afterEach(() => {
	cleanup()
})
