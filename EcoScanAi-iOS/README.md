# EcoScan AI iOS (SwiftUI)

Native iOS app with real-time barcode scanning (AVFoundation), Open Food Facts lookup, impact scoring, disposal instructions, scan history, analytics, sharing, and monthly PDF reporting.

## Requirements

- Xcode 15+
- iOS 16+

## Run

1. Open `/Users/itsak/Desktop/AK_Git_Project_Repos/EcoScanAI/EcoScanAI-iOS/EcoScanAI.xcodeproj` in Xcode.
2. Select an iPhone simulator/device.
3. Build and run (`Cmd+R`).
4. Grant camera permission for live barcode scanning.

## Architecture

- `Models/`: Product, Scan, Impact, Disposal data models
- `Services/`: API, scoring, disposal, barcode scanner, Core Data persistence, PDF export
- `ViewModels/`: scanner, history, analytics logic with Combine
- `Views/`: SwiftUI UI components and screens

## Notes

- Open Food Facts endpoint: `https://world.openfoodfacts.org/api/v2/product/{barcode}.json`
- CO2 mapping:
  - Red = 5.0 kg
  - Yellow = 2.5 kg
  - Green = 0.8 kg
