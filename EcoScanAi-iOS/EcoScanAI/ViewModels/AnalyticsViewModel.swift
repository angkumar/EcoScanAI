import Foundation
import Combine

@MainActor
final class AnalyticsViewModel: ObservableObject {
    @Published private(set) var weeklyCO2Series: [DailyCO2Point] = []
    @Published private(set) var impactCounts: [ImpactScore: Int] = [:]

    private let scanStore: ScanStore
    private let reportService: PDFReportService
    private var cancellables = Set<AnyCancellable>()

    init(scanStore: ScanStore, reportService: PDFReportService) {
        self.scanStore = scanStore
        self.reportService = reportService

        scanStore.scansPublisher
            .sink { [weak self] scans in
                self?.recompute(scans: scans)
            }
            .store(in: &cancellables)
    }

    func exportMonthlyReport(for month: Date) throws -> URL {
        let scans = scanStore.monthlyReport(month: month)
        return try reportService.generateMonthlyReport(scans: scans, for: month)
    }

    private func recompute(scans: [ScanRecord]) {
        let calendar = Calendar.current
        let now = Date()

        var dayBuckets: [Date: Double] = [:]
        for offset in 0..<7 {
            if let day = calendar.date(byAdding: .day, value: -offset, to: now) {
                let key = calendar.startOfDay(for: day)
                dayBuckets[key] = 0
            }
        }

        for scan in scans {
            let key = calendar.startOfDay(for: scan.timestamp)
            if dayBuckets[key] != nil {
                dayBuckets[key, default: 0] += scan.co2Estimate
            }
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "EEE"

        weeklyCO2Series = dayBuckets.keys.sorted().map {
            DailyCO2Point(day: formatter.string(from: $0), value: dayBuckets[$0] ?? 0)
        }

        impactCounts = Dictionary(grouping: scans, by: { $0.impactScore }).mapValues(\ .count)
    }
}

struct DailyCO2Point: Identifiable {
    let id = UUID()
    let day: String
    let value: Double
}
