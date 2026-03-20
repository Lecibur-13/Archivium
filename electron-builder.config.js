/** @type {import('electron-builder').Configuration} */
module.exports = {
  appId: 'com.archivium.app',
  productName: 'Archivium',
  copyright: 'Copyright © 2026 APOLO',
  directories: {
    output: 'release'
  },
  files: [
    'dist/**/*',
    'dist-electron/**/*'
  ],
  asarUnpack: [
    'img/**/*'
  ],
  extraResources: [
    { from: 'img', to: 'img' }
  ],
  win: {
    icon: 'img/logo.ico',
    signingHashAlgorithms: null,
    sign: null,
    target: [
      { target: 'nsis', arch: ['x64'] },
      { target: 'portable', arch: ['x64'] }
    ]
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: true,
    createStartMenuShortcut: true
  },
  linux: {
    icon: 'img/logo.PNG',
    target: [
      { target: 'AppImage', arch: ['x64'] },
      { target: 'deb', arch: ['x64'] }
    ],
    category: 'Utility'
  },
  mac: {
    icon: 'img/logo.PNG',
    target: [
      { target: 'dmg', arch: ['x64', 'arm64'] },
      { target: 'zip', arch: ['x64', 'arm64'] }
    ],
    category: 'public.app-category.utilities',
    identity: null
  }
}
