import UIKit

final class PDFReportService {
    func generateMonthlyReport(scans: [ScanRecord], for date: Date) throws -> URL {
        let formatter = DateFormatter()
        formatter.dateFormat = "LLLL yyyy"
        let title = "EcoScan AI Monthly Report - \(formatter.string(from: date))"

        let pageRect = CGRect(x: 0, y: 0, width: 595, height: 842)
        let renderer = UIGraphicsPDFRenderer(bounds: pageRect)

        let outputURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("ecoscan_monthly_report.pdf")

        try renderer.writePDF(to: outputURL) { context in
            context.beginPage()

            let titleAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.boldSystemFont(ofSize: 22),
                .foregroundColor: UIColor.black
            ]
            title.draw(in: CGRect(x: 30, y: 40, width: pageRect.width - 60, height: 30), withAttributes: titleAttrs)

            let summary = "Total Scans: \(scans.count)\nTotal CO2 Estimate: \(String(format: "%.1f", scans.reduce(0) { $0 + $1.co2Estimate })) kg"
            summary.draw(in: CGRect(x: 30, y: 90, width: pageRect.width - 60, height: 50), withAttributes: [.font: UIFont.systemFont(ofSize: 14)])

            var y: CGFloat = 170
            for scan in scans.prefix(24) {
                let row = "• \(scan.productName) | \(scan.impactScore.rawValue) | \(String(format: "%.1f", scan.co2Estimate)) kg | \(scan.city.rawValue)"
                row.draw(in: CGRect(x: 34, y: y, width: pageRect.width - 68, height: 18), withAttributes: [.font: UIFont.systemFont(ofSize: 12)])
                y += 22
            }
        }

        return outputURL
    }
}
