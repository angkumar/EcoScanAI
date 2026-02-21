import Foundation
import Combine

@MainActor
final class HistoryViewModel: ObservableObject {
    @Published private(set) var scans: [ScanRecord] = []
    @Published private(set) var weeklySummary: WeeklySummary = .empty

    private let scanStore: ScanStore
    private var cancellables = Set<AnyCancellable>()

    init(scanStore: ScanStore) {
        self.scanStore = scanStore

        scanStore.scansPublisher
            .sink { [weak self] scans in
                guard let self else { return }
                self.scans = scans
                self.weeklySummary = WeeklySummary.from(scans: scans)
            }
            .store(in: &cancellables)
    }

    func refresh() {
        scanStore.fetchAll()
    }
}

struct WeeklySummary {
    let totalScans: Int
    let totalCO2: Double
    let streakDays: Int

    static let empty = WeeklySummary(totalScans: 0, totalCO2: 0, streakDays: 0)

    static func from(scans: [ScanRecord]) -> WeeklySummary {
        let calendar = Calendar.current
        let now = Date()
        let weekAgo = calendar.date(byAdding: .day, value: -7, to: now) ?? now
        let weeklyScans = scans.filter { $0.timestamp >= weekAgo }
        let totalCO2 = weeklyScans.reduce(0) { $0 + $1.co2Estimate }

        let groupedDays = Set(scans.map { calendar.startOfDay(for: $0.timestamp) })
        var streak = 0
        var cursor = calendar.startOfDay(for: now)
        while groupedDays.contains(cursor) {
            streak += 1
            guard let previous = calendar.date(byAdding: .day, value: -1, to: cursor) else { break }
            cursor = previous
        }

        return WeeklySummary(totalScans: weeklyScans.count, totalCO2: totalCO2, streakDays: streak)
    }
}
