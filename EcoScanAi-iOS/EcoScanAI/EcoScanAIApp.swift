import SwiftUI

@main
struct EcoScanAIApp: App {
    @StateObject private var appContainer = AppContainer()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(appContainer)
        }
    }
}
