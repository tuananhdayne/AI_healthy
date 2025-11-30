import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

interface FeatureCard {
  title: string;
  description: string;
  icon: string;
  tag: string;
}

interface WorkflowStep {
  title: string;
  description: string;
  badge: string;
}

interface Testimonial {
  quote: string;
  author: string;
  role: string;
}

interface Faq {
  question: string;
  answer: string;
}

@Component({
  selector: 'app-landing',
  templateUrl: './landing.component.html',
  styleUrls: ['./landing.component.scss']
})
export class LandingComponent {
  constructor(private authService: AuthService, private router: Router) {}

  heroStats = [
    { value: '50K+', label: 'Câu hỏi sức khỏe được giải đáp' },
    { value: '24/7', label: 'Theo dõi & hỗ trợ tức thời' },
    { value: '98%', label: 'Người dùng đánh giá tích cực' }
  ];

  featureCards: FeatureCard[] = [
    {
      title: 'Tư vấn tức thì',
      description: 'Nhận câu trả lời dựa trên dữ liệu y khoa chuẩn hóa trong vài giây.',
      icon: '⚡',
      tag: 'Realtime'
    },
    {
      title: 'Cá nhân hóa sâu',
      description: 'HealthyAI ghi nhớ bối cảnh và nhắc bạn theo dõi các chỉ số quan trọng.',
      icon: '🧠',
      tag: 'Insight'
    },
    {
      title: 'An toàn & bảo mật',
      description: 'Mã hóa đầu-cuối, kiểm duyệt nội dung và cảnh báo rủi ro rõ ràng.',
      icon: '🔒',
      tag: 'Safety'
    },
    {
      title: 'Kết nối chuyên gia',
      description: 'Tổng hợp câu hỏi để bạn dễ dàng chia sẻ với bác sĩ của mình.',
      icon: '🤝',
      tag: 'Care team'
    }
  ];

  careHighlights = [
    { title: 'Dinh dưỡng & lối sống', caption: 'Thực đơn, cân nặng, giấc ngủ' },
    { title: 'Sức khỏe tinh thần', caption: 'Thói quen thư giãn, cân bằng cảm xúc' },
    { title: 'Chỉ số luyện tập', caption: 'Kế hoạch cardio, sức bền, nhịp tim' },
    { title: 'Theo dõi bệnh mãn tính', caption: 'Đái tháo đường, huyết áp, mỡ máu' }
  ];

  workflow: WorkflowStep[] = [
    {
      badge: 'Bước 1',
      title: 'Đăng nhập hoặc tạo tài khoản',
      description: 'Chỉ mất 60 giây để thiết lập hồ sơ sức khỏe ban đầu của bạn.'
    },
    {
      badge: 'Bước 2',
      title: 'Đặt câu hỏi hoặc nhập triệu chứng',
      description: 'HealthyAI tự động phân tích, hỏi lại nếu thiếu dữ liệu quan trọng.'
    },
    {
      badge: 'Bước 3',
      title: 'Nhận khuyến nghị an toàn',
      description: 'Hệ thống phân loại mức độ khẩn cấp và đề xuất hành động rõ ràng.'
    }
  ];

  testimonials: Testimonial[] = [
    {
      quote: 'HealthyAI giúp đội ngũ của tôi theo dõi tình trạng nhân viên từ xa mà không gây áp lực.',
      author: 'Minh Anh',
      role: 'HR Lead tại WellCare'
    },
    {
      quote: 'Tôi nhận được lời nhắc uống thuốc và thực đơn phù hợp với huyết áp của mình mỗi ngày.',
      author: 'Chú Hùng',
      role: 'Người dùng kiểm soát huyết áp'
    },
    {
      quote: 'Các câu trả lời luôn đi kèm cảnh báo rõ ràng khi cần gặp bác sĩ, rất trách nhiệm.',
      author: 'BS. Thu Hà',
      role: 'Bác sĩ nội tổng quát'
    }
  ];

  faqs: Faq[] = [
    {
      question: 'HealthyAI có thay thế bác sĩ không?',
      answer: 'Không. HealthyAI chỉ đóng vai trò hỗ trợ, gợi ý thông tin và nhắc bạn gặp chuyên gia khi cần thiết.'
    },
    {
      question: 'Dữ liệu của tôi có an toàn?',
      answer: 'Toàn bộ thông tin được mã hóa, lưu trữ trong vùng bảo mật và bạn có thể yêu cầu xóa bất kỳ lúc nào.'
    },
    {
      question: 'Tôi có thể sử dụng miễn phí không?',
      answer: 'Bạn có thể trò chuyện miễn phí với HealthyAI. Các gói cao hơn hỗ trợ báo cáo chuyên sâu và kết nối bác sĩ.'
    }
  ];

  contactChannels = [
    { label: 'Email', value: 'support@healthyai.vn' },
    { label: 'Hotline', value: '1900 636 808' },
    { label: 'Cộng đồng', value: 't.me/healthyai-community' }
  ];
}
