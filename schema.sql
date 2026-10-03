CREATE DATABASE IF NOT EXISTS foodlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE foodlink;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  mobile VARCHAR(30) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  address VARCHAR(255) NOT NULL,
  role ENUM('donor','ngo','consumer','admin') NOT NULL,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_users_role (role)
) ENGINE=InnoDB;

CREATE TABLE food (
  id INT AUTO_INCREMENT PRIMARY KEY,
  donor_id INT NOT NULL,
  name VARCHAR(140) NOT NULL,
  category VARCHAR(60) NOT NULL,
  quantity DECIMAL(10,2) NOT NULL,
  unit VARCHAR(24) NOT NULL DEFAULT 'servings',
  servings INT NOT NULL,
  food_type VARCHAR(24) NOT NULL,
  prepared_at DATETIME NOT NULL,
  available_until DATETIME NOT NULL,
  storage VARCHAR(80) NOT NULL,
  donation_type ENUM('Free','Discounted') NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0,
  location VARCHAR(255) NOT NULL,
  image VARCHAR(255),
  status VARCHAR(24) NOT NULL DEFAULT 'Available',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_food_status_until (status, available_until),
  CONSTRAINT fk_food_donor FOREIGN KEY (donor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE food_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  food_id INT NOT NULL,
  requester_id INT NOT NULL,
  requested_quantity DECIMAL(10,2) NOT NULL,
  approved_quantity DECIMAL(10,2),
  pickup_at DATETIME NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Requested',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_request_food FOREIGN KEY (food_id) REFERENCES food(id) ON DELETE CASCADE,
  CONSTRAINT fk_request_user FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_request_status (status)
) ENGINE=InnoDB;

CREATE TABLE pickup (
  id INT AUTO_INCREMENT PRIMARY KEY,
  request_id INT NOT NULL UNIQUE,
  status VARCHAR(24) NOT NULL DEFAULT 'Approved',
  pickup_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_pickup_request FOREIGN KEY (request_id) REFERENCES food_requests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  message VARCHAR(255) NOT NULL,
  kind VARCHAR(40) NOT NULL DEFAULT 'update',
  `read` BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notifications_unread (user_id, `read`),
  CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE emergency_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ngo_id INT NOT NULL,
  food_type VARCHAR(100) NOT NULL,
  quantity VARCHAR(100) NOT NULL,
  location VARCHAR(255) NOT NULL,
  required_at DATETIME NOT NULL,
  urgency VARCHAR(20) NOT NULL,
  contact VARCHAR(100) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Open',
  CONSTRAINT fk_emergency_ngo FOREIGN KEY (ngo_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE food_analytics (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  food_id INT NOT NULL,
  event_type ENUM('listed','requested','collected','completed') NOT NULL,
  servings INT NOT NULL DEFAULT 0,
  occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_analytics_type_date (event_type, occurred_at),
  CONSTRAINT fk_analytics_food FOREIGN KEY (food_id) REFERENCES food(id) ON DELETE CASCADE
) ENGINE=InnoDB;
